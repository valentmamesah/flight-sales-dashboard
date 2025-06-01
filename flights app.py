import streamlit as st
import time
from datetime import datetime, date
import pandas as pd
from pymongo import MongoClient
from neo4j import GraphDatabase
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------------------------------
# KONFIGURASI STREAMLIT
# ----------------------------------------
st.set_page_config(
    page_title="Analisis Penjualan Tiket & Perbandingan Performa",
    page_icon="✈️",
    layout="wide"
)

# ----------------------------------------
# FUNGSI UNTUK MEMBUAT DAN MENGHAPUS INDEX
# ----------------------------------------
def create_mongodb_indexes(mongo_db):
    """Membuat index MongoDB"""
    orders = mongo_db["orders"]
    flight_prices = mongo_db["flight_prices"]

    try:
        orders.create_index([("depart_date", 1)], name="idx_depart_date")
        orders.create_index([("flight_id", 1)], name="idx_flight_id")
        orders.create_index([("origin", 1), ("destination", 1), ("depart_date", 1)], name="idx_origin_dest_date")
        flight_prices.create_index([("id", 1)], name="idx_fp_id")
        return True
    except Exception as e:
        st.error(f"Error creating MongoDB indexes: {e}")
        return False

def create_neo4j_indexes(tx):
    """Membuat index Neo4j"""
    tx.run("""
    CREATE INDEX idx_airport_code IF NOT EXISTS
    FOR (a:Airport)
    ON (a.airport_code);
    """)
    tx.run("""
    CREATE INDEX idx_ct_distance_time IF NOT EXISTS
    FOR ()-[r:CONNECTED_TO]-()
    ON (r.distance_km, r.flight_time_hr);
    """)

def drop_mongodb_indexes(mongo_db):
    """Menghapus index MongoDB"""
    orders = mongo_db["orders"]
    flight_prices = mongo_db["flight_prices"]

    try:
        orders.drop_index("idx_depart_date")
        orders.drop_index("idx_flight_id")
        orders.drop_index("idx_origin_dest_date")
        flight_prices.drop_index("idx_fp_id")
        return True
    except Exception as e:
        st.error(f"Error dropping MongoDB indexes: {e}")
        return False

def drop_neo4j_indexes(tx):
    """Menghapus index Neo4j"""
    tx.run("DROP INDEX idx_airport_code IF EXISTS")
    tx.run("DROP INDEX idx_ct_distance_time IF EXISTS")

# ----------------------------------------
# FUNGSI KONEKSI DATABASE
# ----------------------------------------
def init_connections():
    """Inisialisasi koneksi database"""
    NEO4J_URI = "neo4j+s://e4d78cf5.databases.neo4j.io"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "fneMq077AlzF6eFyYsN0ib4ozV54QxyVNitjXx7unIc"
    MONGO_URI = "mongodb+srv://mongodb:akuvalent@cluster0.zq9clry.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        # Neo4j connection
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        
        # MongoDB connection
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        mongo_db = mongo_client["ticketing"]
        
        return driver, mongo_client, mongo_db
    except Exception as e:
        st.error(f"Error connecting to databases: {e}")
        return None, None, None

# ----------------------------------------
# FUNGSI QUERY ANALISIS
# ----------------------------------------
def get_sales_by_date(orders_collection, start_date, end_date):
    """Hitung penjualan harian dalam periode"""
    pipeline_daily = [
        {
            "$match": {
                "depart_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$depart_date"
                    }
                },
                "daily_sales": { "$sum": "$total_price" },
                "daily_orders": { "$sum": 1 }
            }
        },
        {
            "$sort": { "_id": 1 }
        }
    ]
    
    start_time = time.time()
    res_daily = list(orders_collection.aggregate(pipeline_daily))
    end_time = time.time()
    
    df_daily = pd.DataFrame([{
        "date": doc["_id"],
        "daily_sales": doc["daily_sales"],
        "daily_orders": doc["daily_orders"]
    } for doc in res_daily])
    
    if not df_daily.empty:
        df_daily['date'] = pd.to_datetime(df_daily['date'])
    
    duration = end_time - start_time
    return df_daily, duration

# ----------------------------------------
# SKENARIO 1: TANPA OPTIMIZATION
# ----------------------------------------
def run_scenario_1(orders_collection, driver, start_date, end_date):
    """Skenario tanpa indexing dan tanpa query optimization"""
    results = {}
    
    # 1. Total Penjualan
    pipeline_total = [
        {"$match": {"depart_date": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {"_id": None, "totalPenjualan": {"$sum": "$total_price"}, "totalOrders": {"$sum": 1}}}
    ]
    
    start_time = time.time()
    res_total = list(orders_collection.aggregate(pipeline_total))
    results['mongo_total_time'] = time.time() - start_time
    
    results['total_sales'] = res_total[0]["totalPenjualan"] if res_total else 0
    results['total_orders'] = res_total[0]["totalOrders"] if res_total else 0
    
    # 2. Trend harian
    df_daily, daily_time = get_sales_by_date(orders_collection, start_date, end_date)
    results['daily_trend_time'] = daily_time
    results['df_daily'] = df_daily
    
    # 3. Ambil rute terjauh dari Neo4j
    def get_routes(tx):
        return list(tx.run("""
        MATCH (a:Airport)-[r:CONNECTED_TO]->(b:Airport)
        RETURN a.airport_code AS origin, b.airport_code AS destination, 
               r.distance_km AS distance_km, r.flight_time_hr AS flight_time_hr
        ORDER BY r.distance_km DESC LIMIT 50
        """))
    
    start_time = time.time()
    with driver.session() as session:
        route_records = session.execute_read(get_routes)
    results['neo4j_time'] = time.time() - start_time
    
    df_routes = pd.DataFrame([{
        "origin": rec["origin"], "destination": rec["destination"],
        "distance_km": rec["distance_km"], "flight_time_hr": rec["flight_time_hr"]
    } for rec in route_records])
    
    # 4. Hitung penjualan per rute (INDIVIDUAL QUERIES - TIDAK OPTIMAL)
    start_time = time.time()
    route_sales = []
    
    for _, row in df_routes.iterrows():
        pipeline_route = [
            {"$match": {
                "origin": row["origin"], "destination": row["destination"],
                "depart_date": {"$gte": start_date, "$lte": end_date}
            }},
            {"$group": {"_id": None, "totalPenjualan": {"$sum": "$total_price"}, "jumlahOrder": {"$sum": 1}}}
        ]
        
        res_route = list(orders_collection.aggregate(pipeline_route))
        if res_route:
            route_sales.append({
                "origin": row["origin"], "destination": row["destination"],
                "total_penjualan_rute": res_route[0]["totalPenjualan"],
                "jumlah_order_rute": res_route[0]["jumlahOrder"]
            })
        else:
            route_sales.append({
                "origin": row["origin"], "destination": row["destination"],
                "total_penjualan_rute": 0, "jumlah_order_rute": 0
            })
    
    results['mongo_routes_time'] = time.time() - start_time
    
    # 5. Gabungkan data
    df_sales = pd.DataFrame(route_sales)
    df_combined = pd.merge(df_routes, df_sales, on=["origin", "destination"], how="left")
    df_combined[["total_penjualan_rute", "jumlah_order_rute"]] = df_combined[["total_penjualan_rute", "jumlah_order_rute"]].fillna(0)
    results['df_sorted'] = df_combined.sort_values(by="total_penjualan_rute", ascending=False)
    
    return results

# ----------------------------------------
# SKENARIO 2: DENGAN OPTIMIZATION
# ----------------------------------------
def run_scenario_2(orders_collection, driver, start_date, end_date):
    """Skenario dengan indexing dan query optimization"""
    results = {}
    
    # 1. Total Penjualan (sama seperti skenario 1)
    pipeline_total = [
        {"$match": {"depart_date": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {"_id": None, "totalPenjualan": {"$sum": "$total_price"}, "totalOrders": {"$sum": 1}}}
    ]
    
    start_time = time.time()
    res_total = list(orders_collection.aggregate(pipeline_total))
    results['mongo_total_time'] = time.time() - start_time
    
    results['total_sales'] = res_total[0]["totalPenjualan"] if res_total else 0
    results['total_orders'] = res_total[0]["totalOrders"] if res_total else 0
    
    # 2. Trend harian
    df_daily, daily_time = get_sales_by_date(orders_collection, start_date, end_date)
    results['daily_trend_time'] = daily_time
    results['df_daily'] = df_daily
    
    # 3. Ambil rute terjauh dari Neo4j (sama)
    def get_routes(tx):
        return list(tx.run("""
        MATCH (a:Airport)-[r:CONNECTED_TO]->(b:Airport)
        WHERE r.distance_km > 1000 AND r.flight_time_hr IS NOT NULL
        RETURN a.airport_code AS origin, b.airport_code AS destination, 
               r.distance_km AS distance_km, r.flight_time_hr AS flight_time_hr
        ORDER BY r.distance_km DESC LIMIT 50
        """))
    
    start_time = time.time()
    with driver.session() as session:
        route_records = session.execute_read(get_routes)
    results['neo4j_time'] = time.time() - start_time
    
    df_routes = pd.DataFrame([{
        "origin": rec["origin"], "destination": rec["destination"],
        "distance_km": rec["distance_km"], "flight_time_hr": rec["flight_time_hr"]
    } for rec in route_records])
    
    # 4. Hitung penjualan per rute (BATCH QUERY - OPTIMAL)
    start_time = time.time()
    origin_list = df_routes["origin"].unique().tolist()
    destination_list = df_routes["destination"].unique().tolist()
    
    pipeline_batch = [
        {"$match": {
            "depart_date": {"$gte": start_date, "$lte": end_date},
            "origin": {"$in": origin_list},
            "destination": {"$in": destination_list}
        }},
        {"$group": {
            "_id": {"origin": "$origin", "destination": "$destination"},
            "total_penjualan_rute": {"$sum": "$total_price"},
            "jumlah_order_rute": {"$sum": 1}
        }}
    ]
    
    res_batch = list(orders_collection.aggregate(pipeline_batch))
    results['mongo_routes_time'] = time.time() - start_time
    
    df_batch = pd.DataFrame([{
        "origin": doc["_id"]["origin"], "destination": doc["_id"]["destination"],
        "total_penjualan_rute": doc["total_penjualan_rute"],
        "jumlah_order_rute": doc["jumlah_order_rute"]
    } for doc in res_batch])
    
    # 5. Gabungkan data
    df_combined = pd.merge(df_routes, df_batch, on=["origin", "destination"], how="left")
    df_combined[["total_penjualan_rute", "jumlah_order_rute"]] = df_combined[["total_penjualan_rute", "jumlah_order_rute"]].fillna(0)
    results['df_sorted'] = df_combined.sort_values(by="total_penjualan_rute", ascending=False)
    
    return results

# ----------------------------------------
# FUNGSI UNTUK ANALISIS INSIGHT
# ----------------------------------------
def generate_insights(results1, results2, period_days):
    """Generate business insights dari hasil analisis"""
    insights = []
    
    # Data dari hasil optimized
    total_sales = results2['total_sales']
    total_orders = results2['total_orders']
    df_daily = results2['df_daily']
    df_sorted = results2['df_sorted']
    
    # 1. Performance Insight
    if 'total_time1' in st.session_state and 'total_time2' in st.session_state:
        time1 = st.session_state['total_time1']
        time2 = st.session_state['total_time2']
        improvement = ((time1 - time2) / time1) * 100
        insights.append({
            "type": "performance",
            "title": "💡 Performance Optimization Impact",
            "content": f"Dengan optimasi database, performa meningkat **{improvement:.1f}%** dari {time1:.2f}s menjadi {time2:.2f}s. Ini menunjukkan pentingnya indexing dan batch query processing."
        })
    
    # 2. Sales Pattern Insight
    avg_daily = total_sales / period_days if period_days > 0 else 0
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    insights.append({
        "type": "sales",
        "title": "📊 Sales Performance Overview",
        "content": f"Dalam periode {period_days} hari, terjadi **{total_orders:,} transaksi** dengan total penjualan **Rp {total_sales:,}**. Rata-rata nilai order **Rp {avg_order_value:,.0f}** dan rata-rata penjualan harian **Rp {avg_daily:,.0f}**."
    })
    
    # 3. Daily Trend Insight
    if not df_daily.empty:
        max_day = df_daily.loc[df_daily['daily_sales'].idxmax()]
        min_day = df_daily.loc[df_daily['daily_sales'].idxmin()]
        
        insights.append({
            "type": "trend",
            "title": "📈 Daily Sales Trend Analysis",
            "content": f"Penjualan tertinggi terjadi pada **{max_day['date'].strftime('%d %B %Y')}** dengan **Rp {max_day['daily_sales']:,.0f}**. Penjualan terendah pada **{min_day['date'].strftime('%d %B %Y')}** sebesar **Rp {min_day['daily_sales']:,.0f}**."
        })
    
    # 4. Route Performance Insight
    if not df_sorted.empty:
        top_routes = df_sorted[df_sorted['total_penjualan_rute'] > 0].head(5)
        if not top_routes.empty:
            top_route = top_routes.iloc[0]
            total_route_sales = top_routes['total_penjualan_rute'].sum()
            route_contribution = (total_route_sales / total_sales) * 100
            
            insights.append({
                "type": "route",
                "title": "🛫 Route Performance Analysis",
                "content": f"Rute terlaris adalah **{top_route['origin']} → {top_route['destination']}** dengan penjualan **Rp {top_route['total_penjualan_rute']:,.0f}** ({top_route['jumlah_order_rute']:.0f} orders). Top 5 rute berkontribusi **{route_contribution:.1f}%** dari total penjualan."
            })
        
        # Distance vs Sales Analysis
        routes_with_sales = df_sorted[df_sorted['total_penjualan_rute'] > 0]
        if len(routes_with_sales) > 10:
            correlation = routes_with_sales['distance_km'].corr(routes_with_sales['total_penjualan_rute'])
            correlation_strength = "lemah" if abs(correlation) < 0.3 else "sedang" if abs(correlation) < 0.7 else "kuat"
            correlation_direction = "positif" if correlation > 0 else "negatif"
            
            insights.append({
                "type": "correlation",
                "title": "📏 Distance vs Sales Correlation",
                "content": f"Korelasi antara jarak rute dan penjualan adalah **{correlation:.3f}** (korelasi {correlation_strength} {correlation_direction}). Ini menunjukkan bahwa jarak rute {'memiliki' if abs(correlation) > 0.3 else 'tidak memiliki'} pengaruh signifikan terhadap volume penjualan."
            })
    
    # 5. Business Recommendation
    recommendations = []
    
    if not df_daily.empty:
        # Identifikasi hari dengan penjualan rendah
        low_sales_threshold = df_daily['daily_sales'].quantile(0.25)
        low_sales_days = len(df_daily[df_daily['daily_sales'] <= low_sales_threshold])
        
        if low_sales_days > 0:
            recommendations.append(f"Fokus pada strategi marketing untuk {low_sales_days} hari dengan penjualan rendah")
    
    if not df_sorted.empty:
        zero_sales_routes = len(df_sorted[df_sorted['total_penjualan_rute'] == 0])
        if zero_sales_routes > 0:
            recommendations.append(f"Evaluasi dan optimalkan {zero_sales_routes} rute yang tidak menghasilkan penjualan")
    
    if recommendations:
        insights.append({
            "type": "recommendation",
            "title": "💼 Business Recommendations",
            "content": "• " + "\n• ".join(recommendations)
        })
    
    return insights

# ----------------------------------------
# MAIN APP
# ----------------------------------------
def main():
    st.title("✈️ Analisis Penjualan Tiket & Perbandingan Performa Database")
    st.markdown("**Comprehensive Analysis: Business Insights + Database Performance Comparison**")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.header("⚙️ Konfigurasi")
    
    # Periode analisis
    st.sidebar.subheader("📅 Periode Analisis")
    preset = st.sidebar.selectbox("Preset Periode:", ["Ramadhan 2023", "Custom"])
    
    if preset == "Ramadhan 2023":
        start_date = date(2023, 3, 10)
        end_date = date(2023, 4, 9)
    else:
        start_date = st.sidebar.date_input("Tanggal Mulai", value=date(2023, 3, 10))
        end_date = st.sidebar.date_input("Tanggal Selesai", value=date(2023, 4, 9))
    
    if start_date > end_date:
        st.sidebar.error("❌ Tanggal mulai tidak boleh lebih besar dari tanggal selesai!")
        st.stop()
    
    period_days = (end_date - start_date).days + 1
    st.sidebar.info(f"📊 Periode: {period_days} hari")
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Index Management
    st.sidebar.subheader("🔧 Index Management")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("➕ Buat Index", use_container_width=True):
            with st.spinner("Membuat indexes..."):
                driver, mongo_client, mongo_db = init_connections()
                if driver and mongo_client:
                    try:
                        create_mongodb_indexes(mongo_db)
                        with driver.session() as session:
                            session.execute_write(create_neo4j_indexes)
                        st.sidebar.success("✅ Indexes dibuat!")
                    except Exception as e:
                        st.sidebar.error(f"❌ Error: {e}")
                    finally:
                        if driver: driver.close()
                        if mongo_client: mongo_client.close()
    
    with col2:
        if st.button("➖ Hapus Index", use_container_width=True):
            with st.spinner("Menghapus indexes..."):
                driver, mongo_client, mongo_db = init_connections()
                if driver and mongo_client:
                    try:
                        drop_mongodb_indexes(mongo_db)
                        with driver.session() as session:
                            session.execute_write(drop_neo4j_indexes)
                        st.sidebar.success("✅ Indexes dihapus!")
                    except Exception as e:
                        st.sidebar.error(f"❌ Error: {e}")
                    finally:
                        if driver: driver.close()
                        if mongo_client: mongo_client.close()
    
    # Tabs untuk semua fitur
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🐌 Tanpa Optimization", 
        "⚡ Dengan Optimization", 
        "📊 Perbandingan Performa",
        "💡 Business Insights",
        "📈 Visualisasi Data"
    ])
    
    # TAB 1: TANPA OPTIMIZATION
    with tab1:
        st.header("🐌 Skenario 1: Tanpa Indexing & Optimization")
        
        if st.button("🚀 Jalankan Skenario 1", key="scenario1"):
            with st.spinner("Menjalankan analisis tanpa optimization..."):
                total_start = time.time()
                
                driver, mongo_client, mongo_db = init_connections()
                if not driver or not mongo_client:
                    st.error("❌ Gagal terhubung ke database!")
                    return
                
                try:
                    orders_collection = mongo_db["orders"]
                    results1 = run_scenario_1(orders_collection, driver, start_datetime, end_datetime)
                    total_time1 = time.time() - total_start
                    
                    # Store in session state
                    st.session_state['results1'] = results1
                    st.session_state['total_time1'] = total_time1
                    
                finally:
                    if driver: driver.close()
                    if mongo_client: mongo_client.close()
        
        # Display results if available
        if 'results1' in st.session_state:
            results = st.session_state['results1']
            total_time = st.session_state['total_time1']
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 Total Penjualan", f"Rp {results['total_sales']:,}")
            with col2:
                st.metric("📦 Total Orders", f"{results['total_orders']:,}")
            with col3:
                avg_order = results['total_sales'] / results['total_orders'] if results['total_orders'] > 0 else 0
                st.metric("💳 Rata-rata Order", f"Rp {avg_order:,.0f}")
            with col4:
                st.metric("⏱️ Total Waktu", f"{total_time:.2f}s")
            
            # Performance breakdown
            st.subheader("📈 Performance Breakdown")
            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
            with perf_col1:
                st.metric("MongoDB Total Sales", f"{results['mongo_total_time']:.4f}s")
            with perf_col2:
                st.metric("Daily Trend Query", f"{results['daily_trend_time']:.4f}s")
            with perf_col3:
                st.metric("Neo4j Routes Query", f"{results['neo4j_time']:.4f}s")
            with perf_col4:
                st.metric("MongoDB Routes (Individual)", f"{results['mongo_routes_time']:.4f}s")
            
            # Top routes
            st.subheader("🏆 Top 10 Rute Terlaris")
            top_routes = results['df_sorted'][results['df_sorted']['total_penjualan_rute'] > 0].head(10)
            if not top_routes.empty:
                st.dataframe(
                    top_routes[['origin', 'destination', 'distance_km', 'total_penjualan_rute', 'jumlah_order_rute']],
                    use_container_width=True,
                    column_config={
                        "distance_km": st.column_config.NumberColumn("Jarak (km)", format="%.0f"),
                        "total_penjualan_rute": st.column_config.NumberColumn("Penjualan", format="Rp %.0f"),
                        "jumlah_order_rute": st.column_config.NumberColumn("Orders", format="%.0f")
                    }
                )
    
    # TAB 2: DENGAN OPTIMIZATION
    with tab2:
        st.header("⚡ Skenario 2: Dengan Indexing & Optimization")
        
        if st.button("🚀 Jalankan Skenario 2", key="scenario2"):
            with st.spinner("Menjalankan analisis dengan optimization..."):
                total_start = time.time()
                
                driver, mongo_client, mongo_db = init_connections()
                if not driver or not mongo_client:
                    st.error("❌ Gagal terhubung ke database!")
                    return
                
                try:
                    orders_collection = mongo_db["orders"]
                    results2 = run_scenario_2(orders_collection, driver, start_datetime, end_datetime)
                    total_time2 = time.time() - total_start
                    
                    # Store in session state
                    st.session_state['results2'] = results2
                    st.session_state['total_time2'] = total_time2
                    
                finally:
                    if driver: driver.close()
                    if mongo_client: mongo_client.close()
        
        # Display results if available
        if 'results2' in st.session_state:
            results = st.session_state['results2']
            total_time = st.session_state['total_time2']
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 Total Penjualan", f"Rp {results['total_sales']:,}")
            with col2:
                st.metric("📦 Total Orders", f"{results['total_orders']:,}")
            with col3:
                avg_order = results['total_sales'] / results['total_orders'] if results['total_orders'] > 0 else 0
                st.metric("💳 Rata-rata Order", f"Rp {avg_order:,.0f}")
            with col4:
                st.metric("⏱️ Total Waktu", f"{total_time:.2f}s")
            
            # Performance breakdown
            st.subheader("📈 Performance Breakdown")
            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
            with perf_col1:
                st.metric("MongoDB Total Sales", f"{results['mongo_total_time']:.4f}s")
            with perf_col2:
                st.metric("Daily Trend Query", f"{results['daily_trend_time']:.4f}s")
            with perf_col3:
                st.metric("Neo4j Routes Query", f"{results['neo4j_time']:.4f}s")
            with perf_col4:
                st.metric("MongoDB Routes (Batch)", f"{results['mongo_routes_time']:.4f}s")
            
            # Top routes
            st.subheader("🏆 Top 10 Rute Terlaris")
            top_routes = results['df_sorted'][results['df_sorted']['total_penjualan_rute'] > 0].head(10)
            if not top_routes.empty:
                st.dataframe(
                top_routes[['origin', 'destination', 'distance_km', 'total_penjualan_rute', 'jumlah_order_rute']],
                    use_container_width=True,
                    column_config={
                        "distance_km": st.column_config.NumberColumn("Jarak (km)", format="%.0f"),
                        "total_penjualan_rute": st.column_config.NumberColumn("Penjualan", format="Rp %.0f"),
                        "jumlah_order_rute": st.column_config.NumberColumn("Orders", format="%.0f")
                    }
                )
    
    # TAB 3: PERBANDINGAN PERFORMA
    with tab3:
        st.header("📊 Perbandingan Performa Database")
        
        if 'results1' in st.session_state and 'results2' in st.session_state:
            time1 = st.session_state['total_time1']
            time2 = st.session_state['total_time2']
            improvement = ((time1 - time2) / time1) * 100
            
            # Performance comparison metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("⏱️ Tanpa Optimization", f"{time1:.2f}s")
            with col2:
                st.metric("⚡ Dengan Optimization", f"{time2:.2f}s")
            with col3:
                st.metric("🚀 Peningkatan Performa", f"{improvement:.1f}%")
            with col4:
                speedup = time1 / time2 if time2 > 0 else 0
                st.metric("📈 Speedup Factor", f"{speedup:.1f}x")
            
            # Detailed performance breakdown
            st.subheader("🔍 Breakdown Performance Detail")
            
            results1 = st.session_state['results1']
            results2 = st.session_state['results2']
            
            perf_data = {
                "Query Type": [
                    "MongoDB Total Sales",
                    "Daily Trend Query", 
                    "Neo4j Routes Query",
                    "MongoDB Routes Query",
                    "TOTAL"
                ],
                "Tanpa Optimization (s)": [
                    results1['mongo_total_time'],
                    results1['daily_trend_time'],
                    results1['neo4j_time'],
                    results1['mongo_routes_time'],
                    time1
                ],
                "Dengan Optimization (s)": [
                    results2['mongo_total_time'],
                    results2['daily_trend_time'],
                    results2['neo4j_time'],
                    results2['mongo_routes_time'],
                    time2
                ]
            }
            
            df_perf = pd.DataFrame(perf_data)
            df_perf["Improvement (%)"] = ((df_perf["Tanpa Optimization (s)"] - df_perf["Dengan Optimization (s)"]) / df_perf["Tanpa Optimization (s)"]) * 100
            df_perf["Speedup"] = df_perf["Tanpa Optimization (s)"] / df_perf["Dengan Optimization (s)"]
            
            st.dataframe(
                df_perf,
                use_container_width=True,
                column_config={
                    "Tanpa Optimization (s)": st.column_config.NumberColumn("Tanpa Optimization (s)", format="%.4f"),
                    "Dengan Optimization (s)": st.column_config.NumberColumn("Dengan Optimization (s)", format="%.4f"),
                    "Improvement (%)": st.column_config.NumberColumn("Improvement (%)", format="%.1f"),
                    "Speedup": st.column_config.NumberColumn("Speedup", format="%.1f")
                }
            )
            
            # Performance visualization
            st.subheader("📊 Visualisasi Perbandingan Performa")
            
            # Bar chart comparison
            fig_perf = go.Figure()
            
            fig_perf.add_trace(go.Bar(
                name='Tanpa Optimization',
                x=df_perf["Query Type"][:-1],  # Exclude TOTAL
                y=df_perf["Tanpa Optimization (s)"][:-1],
                marker_color='#ff6b6b'
            ))
            
            fig_perf.add_trace(go.Bar(
                name='Dengan Optimization',
                x=df_perf["Query Type"][:-1],
                y=df_perf["Dengan Optimization (s)"][:-1],
                marker_color='#51cf66'
            ))
            
            fig_perf.update_layout(
                title="Performance Comparison by Query Type",
                xaxis_title="Query Type",
                yaxis_title="Execution Time (seconds)",
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig_perf, use_container_width=True)
            
            # Performance insights
            st.subheader("💡 Performance Insights")
            
            # Find the query with biggest improvement
            biggest_improvement_idx = df_perf["Improvement (%)"][:-1].idxmax()  # Exclude TOTAL
            biggest_improvement = df_perf.iloc[biggest_improvement_idx]
            
            st.info(f"""
            **🎯 Key Performance Insights:**
            
            • **Overall Performance**: Optimasi meningkatkan performa sebesar **{improvement:.1f}%** dengan speedup **{speedup:.1f}x**
            
            • **Biggest Impact**: {biggest_improvement['Query Type']} mengalami peningkatan terbesar (**{biggest_improvement['Improvement (%)']:.1f}%**)
            
            • **MongoDB Routes Query**: Perubahan dari individual queries ke batch processing memberikan dampak signifikan
            
            • **Indexing Effect**: Database indexes mempercepat query filtering dan sorting operations
            """)
            
        else:
            st.warning("⚠️ Jalankan kedua skenario terlebih dahulu untuk melihat perbandingan performa!")
    
    # TAB 4: BUSINESS INSIGHTS
    with tab4:
        st.header("💡 Business Insights & Analytics")
        
        if 'results2' in st.session_state:
            results1 = st.session_state.get('results1', {})
            results2 = st.session_state['results2']
            
            # Generate insights
            insights = generate_insights(results1, results2, period_days)
            
            # Display insights
            for insight in insights:
                if insight['type'] == 'performance':
                    st.success(f"**{insight['title']}**\n\n{insight['content']}")
                elif insight['type'] == 'sales':
                    st.info(f"**{insight['title']}**\n\n{insight['content']}")
                elif insight['type'] == 'trend':
                    st.info(f"**{insight['title']}**\n\n{insight['content']}")
                elif insight['type'] == 'route':
                    st.success(f"**{insight['title']}**\n\n{insight['content']}")
                elif insight['type'] == 'correlation':
                    st.info(f"**{insight['title']}**\n\n{insight['content']}")
                elif insight['type'] == 'recommendation':
                    st.warning(f"**{insight['title']}**\n\n{insight['content']}")
            
            # Additional analysis
            st.subheader("📈 Advanced Analytics")
            
            df_sorted = results2['df_sorted']
            df_daily = results2['df_daily']
            
            if not df_sorted.empty and not df_daily.empty:
                # Route efficiency analysis
                routes_with_sales = df_sorted[df_sorted['total_penjualan_rute'] > 0].copy()
                if not routes_with_sales.empty:
                    routes_with_sales['revenue_per_km'] = routes_with_sales['total_penjualan_rute'] / routes_with_sales['distance_km']
                    routes_with_sales['revenue_per_hour'] = routes_with_sales['total_penjualan_rute'] / routes_with_sales['flight_time_hr']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🛫 Most Efficient Routes (Revenue/km)")
                        top_efficient_km = routes_with_sales.nlargest(5, 'revenue_per_km')[
                            ['origin', 'destination', 'distance_km', 'total_penjualan_rute', 'revenue_per_km']
                        ]
                        st.dataframe(
                            top_efficient_km,
                            use_container_width=True,
                            column_config={
                                "revenue_per_km": st.column_config.NumberColumn("Revenue/km", format="Rp %.0f")
                            }
                        )
                    
                    with col2:
                        st.subheader("⏰ Most Efficient Routes (Revenue/hour)")
                        top_efficient_hr = routes_with_sales.nlargest(5, 'revenue_per_hour')[
                            ['origin', 'destination', 'flight_time_hr', 'total_penjualan_rute', 'revenue_per_hour']
                        ]
                        st.dataframe(
                            top_efficient_hr,
                            use_container_width=True,
                            column_config={
                                "revenue_per_hour": st.column_config.NumberColumn("Revenue/hour", format="Rp %.0f")
                            }
                        )
                
                # Daily sales statistics
                if len(df_daily) > 1:
                    st.subheader("📊 Daily Sales Statistics")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("📈 Max Daily Sales", f"Rp {df_daily['daily_sales'].max():,.0f}")
                    with col2:
                        st.metric("📉 Min Daily Sales", f"Rp {df_daily['daily_sales'].min():,.0f}")
                    with col3:
                        st.metric("📊 Average Daily Sales", f"Rp {df_daily['daily_sales'].mean():,.0f}")
                    with col4:
                        std_dev = df_daily['daily_sales'].std()
                        st.metric("📐 Standard Deviation", f"Rp {std_dev:,.0f}")
            
        else:
            st.warning("⚠️ Jalankan skenario dengan optimization terlebih dahulu untuk melihat business insights!")
    
    # TAB 5: VISUALISASI DATA
    with tab5:
        st.header("📈 Visualisasi Data & Dashboard")
        
        if 'results2' in st.session_state:
            results = st.session_state['results2']
            df_daily = results['df_daily']
            df_sorted = results['df_sorted']
            
            # Daily sales trend
            if not df_daily.empty:
                st.subheader("📈 Trend Penjualan Harian")
                
                fig_daily = px.line(
                    df_daily, 
                    x='date', 
                    y='daily_sales',
                    title=f"Daily Sales Trend ({start_date} - {end_date})",
                    labels={'daily_sales': 'Daily Sales (Rp)', 'date': 'Date'}
                )
                fig_daily.update_traces(line_color='#1f77b4', line_width=3)
                fig_daily.update_layout(height=400)
                st.plotly_chart(fig_daily, use_container_width=True)
                
                # Orders vs Sales
                fig_orders = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=('Daily Sales', 'Daily Orders'),
                    specs=[[{"secondary_y": False}, {"secondary_y": False}]]
                )
                
                fig_orders.add_trace(
                    go.Scatter(x=df_daily['date'], y=df_daily['daily_sales'], 
                              mode='lines+markers', name='Sales', line=dict(color='#1f77b4')),
                    row=1, col=1
                )
                
                fig_orders.add_trace(
                    go.Scatter(x=df_daily['date'], y=df_daily['daily_orders'], 
                              mode='lines+markers', name='Orders', line=dict(color='#ff7f0e')),
                    row=1, col=2
                )
                
                fig_orders.update_layout(height=400, title_text="Daily Sales vs Orders Comparison")
                st.plotly_chart(fig_orders, use_container_width=True)
            
            # Route analysis visualizations
            if not df_sorted.empty:
                routes_with_sales = df_sorted[df_sorted['total_penjualan_rute'] > 0]
                
                if not routes_with_sales.empty:
                    st.subheader("🛫 Analisa Rute Penerbangan")
                    
                    # Top routes bar chart
                    top_10_routes = routes_with_sales.head(10)
                    top_10_routes['route'] = top_10_routes['origin'] + ' → ' + top_10_routes['destination']
                    
                    fig_routes = px.bar(
                        top_10_routes,
                        x='total_penjualan_rute',
                        y='route',
                        orientation='h',
                        title="Top 10 Routes by Sales Revenue",
                        labels={'total_penjualan_rute': 'Sales Revenue (Rp)', 'route': 'Route'}
                    )
                    fig_routes.update_layout(height=500)
                    st.plotly_chart(fig_routes, use_container_width=True)
                    
                    # Distance vs Sales scatter plot
                    fig_scatter = px.scatter(
                        routes_with_sales,
                        x='distance_km',
                        y='total_penjualan_rute',
                        size='jumlah_order_rute',
                        hover_data=['origin', 'destination', 'flight_time_hr'],
                        title="Route Distance vs Sales Revenue",
                        labels={
                            'distance_km': 'Distance (km)',
                            'total_penjualan_rute': 'Sales Revenue (Rp)',
                            'jumlah_order_rute': 'Number of Orders'
                        }
                    )
                    fig_scatter.update_layout(height=500)
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # Sales distribution
                    st.subheader("📊 Distribusi Penjualan")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Sales histogram
                        fig_hist = px.histogram(
                            routes_with_sales,
                            x='total_penjualan_rute',
                            nbins=20,
                            title="Sales Revenue Distribution",
                            labels={'total_penjualan_rute': 'Sales Revenue (Rp)'}
                        )
                        st.plotly_chart(fig_hist, use_container_width=True)
                    
                    with col2:
                        # Distance histogram
                        fig_dist = px.histogram(
                            routes_with_sales,
                            x='distance_km',
                            nbins=20,
                            title="Route Distance Distribution",
                            labels={'distance_km': 'Distance (km)'}
                        )
                        st.plotly_chart(fig_dist, use_container_width=True)
                    
                    # Summary statistics table
                    st.subheader("📋 Summary Statistics")
                    
                    summary_stats = {
                        'Revenue': routes_with_sales['total_penjualan_rute'].describe(),
                        'Orders': routes_with_sales['jumlah_order_rute'].describe(),
                        'Distance (km)': routes_with_sales['distance_km'].describe(),
                        'Flight Time (hr)': routes_with_sales['flight_time_hr'].describe()
                    }
                    
                    summary_df = pd.DataFrame(summary_stats).round(2)
                    st.dataframe(summary_df, use_container_width=True)
        
        else:
            st.warning("⚠️ Jalankan analisis terlebih dahulu untuk melihat visualisasi data!")
    
    # Footer
    st.markdown("---")
    st.markdown("**✈️ Flight Ticket Sales Analysis Dashboard** | Built with Streamlit, MongoDB & Neo4j")

if __name__ == "__main__":
    main()
