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
    page_title="Perbandingan Performa Database",
    page_icon="⚡",
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
    
    # 2. Ambil rute terjauh dari Neo4j
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
    
    # 3. Hitung penjualan per rute (INDIVIDUAL QUERIES - TIDAK OPTIMAL)
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
    
    # 4. Gabungkan data
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
    
    # 2. Ambil rute terjauh dari Neo4j (sama)
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
    
    # 3. Hitung penjualan per rute (BATCH QUERY - OPTIMAL)
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
    
    # 4. Gabungkan data
    df_combined = pd.merge(df_routes, df_batch, on=["origin", "destination"], how="left")
    df_combined[["total_penjualan_rute", "jumlah_order_rute"]] = df_combined[["total_penjualan_rute", "jumlah_order_rute"]].fillna(0)
    results['df_sorted'] = df_combined.sort_values(by="total_penjualan_rute", ascending=False)
    
    return results

# ----------------------------------------
# MAIN APP
# ----------------------------------------
def main():
    st.title("⚡ Perbandingan Performa Database")
    st.markdown("**Analisis Penjualan Tiket: Tanpa vs Dengan Optimization**")
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
    
    # Tabs untuk kedua skenario
    tab1, tab2, tab3 = st.tabs(["🐌 Tanpa Optimization", "⚡ Dengan Optimization", "📊 Perbandingan"])
    
    # TAB 1: TANPA OPTIMIZATION
    with tab1:
        st.header("🐌 Skenario 1: Tanpa Indexing & Optimization")
        st.info("📝 **Karakteristik:**\n- Tanpa database indexes\n- Query individual per rute (N+1 queries)\n- Tidak ada batch processing")
        
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
            perf_col1, perf_col2, perf_col3 = st.columns(3)
            with perf_col1:
                st.metric("MongoDB Total Sales", f"{results['mongo_total_time']:.4f}s")
            with perf_col2:
                st.metric("Neo4j Routes Query", f"{results['neo4j_time']:.4f}s")
            with perf_col3:
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
        st.success("📝 **Karakteristik:**\n- Menggunakan database indexes\n- Batch query processing\n- Optimized aggregation pipelines")
        
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
            perf_col1, perf_col2, perf_col3 = st.columns(3)
            with perf_col1:
                st.metric("MongoDB Total Sales", f"{results['mongo_total_time']:.4f}s")
            with perf_col2:
                st.metric("Neo4j Routes Query", f"{results['neo4j_time']:.4f}s")
            with perf_col3:
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
    
    # TAB 3: PERBANDINGAN
    with tab3:
        st.header("📊 Perbandingan Performa")
        
        if 'results1' in st.session_state and 'results2' in st.session_state:
            results1 = st.session_state['results1']
            results2 = st.session_state['results2']
            total_time1 = st.session_state['total_time1']
            total_time2 = st.session_state['total_time2']
            
            # Overall comparison
            st.subheader("🏁 Perbandingan Waktu Total")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("🐌 Tanpa Optimization", f"{total_time1:.2f}s")
            with col2:
                st.metric("⚡ Dengan Optimization", f"{total_time2:.2f}s")
            with col3:
                improvement = ((total_time1 - total_time2) / total_time1) * 100
                st.metric("🚀 Peningkatan", f"{improvement:.1f}%", 
                         delta=f"{total_time1 - total_time2:.2f}s")
            
            # Detailed comparison chart
            st.subheader("📈 Breakdown Performa per Komponen")
            
            comparison_data = pd.DataFrame({
                'Komponen': ['MongoDB Total Sales', 'Neo4j Routes', 'MongoDB Routes Processing'],
                'Tanpa Optimization (s)': [
                    results1['mongo_total_time'],
                    results1['neo4j_time'],
                    results1['mongo_routes_time']
                ],
                'Dengan Optimization (s)': [
                    results2['mongo_total_time'],
                    results2['neo4j_time'],
                    results2['mongo_routes_time']
                ]
            })
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Tanpa Optimization',
                x=comparison_data['Komponen'],
                y=comparison_data['Tanpa Optimization (s)'],
                marker_color='lightcoral'
            ))
            fig.add_trace(go.Bar(
                name='Dengan Optimization',
                x=comparison_data['Komponen'],
                y=comparison_data['Dengan Optimization (s)'],
                marker_color='lightblue'
            ))
            
            fig.update_layout(
                title='Perbandingan Waktu Eksekusi per Komponen',
                xaxis_title='Komponen Query',
                yaxis_title='Waktu (detik)',
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Improvement table
            st.subheader("📋 Tabel Peningkatan Performa")
            improvement_data = []
            components = [
                ('MongoDB Total Sales', results1['mongo_total_time'], results2['mongo_total_time']),
                ('Neo4j Routes', results1['neo4j_time'], results2['neo4j_time']),
                ('MongoDB Routes Processing', results1['mongo_routes_time'], results2['mongo_routes_time']),
                ('Total Waktu', total_time1, total_time2)
            ]
            
            for comp_name, time1, time2 in components:
                improvement_pct = ((time1 - time2) / time1) * 100 if time1 > 0 else 0
                speedup = time1 / time2 if time2 > 0 else 0
                improvement_data.append({
                    'Komponen': comp_name,
                    'Tanpa Optimization': f"{time1:.4f}s",
                    'Dengan Optimization': f"{time2:.4f}s",
                    'Peningkatan (%)': f"{improvement_pct:.1f}%",
                    'Speedup': f"{speedup:.2f}x"
                })
            
            df_improvement = pd.DataFrame(improvement_data)
            st.dataframe(df_improvement, use_container_width=True)
            
            # Key insights
            st.subheader("💡 Key Insights")
            route_improvement = ((results1['mongo_routes_time'] - results2['mongo_routes_time']) / results1['mongo_routes_time']) * 100
            
            st.info(f"""
            **Highlights:**
            - **Total peningkatan performa: {improvement:.1f}%**
            - **MongoDB Routes Processing mengalami peningkatan terbesar: {route_improvement:.1f}%**
            - **Batch processing vs individual queries menunjukkan perbedaan signifikan**
            - **Indexing membantu mempercepat query filtering dan sorting**
            """)
            
        else:
            st.warning("⚠️ Jalankan kedua skenario terlebih dahulu untuk melihat perbandingan!")

if __name__ == "__main__":
    main()
