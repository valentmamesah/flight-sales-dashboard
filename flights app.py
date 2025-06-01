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
    page_title="Analisis Penjualan Tiket",
    page_icon="✈️",
    layout="wide"
)

# ----------------------------------------
# FUNGSI UNTUK MEMBUAT INDEX
# ----------------------------------------
def create_mongodb_indexes(mongo_db):
    """Membuat index MongoDB"""
    orders = mongo_db["orders"]
    flight_prices = mongo_db["flight_prices"]

    try:
        idx_depart_date = orders.create_index(
            [("depart_date", 1)],
            name="idx_depart_date"
        )

        idx_flight_id = orders.create_index(
            [("flight_id", 1)],
            name="idx_flight_id"
        )

        idx_fp_id = flight_prices.create_index(
            [("id", 1)],
            name="idx_fp_id"
        )
        
        idx_origin_dest_date = orders.create_index(
            [("origin", 1), ("destination", 1), ("depart_date", 1)],
            name="idx_origin_dest_date"
        )
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

# ----------------------------------------
# FUNGSI KONEKSI DATABASE
# ----------------------------------------
def init_neo4j_connection():
    """Inisialisasi koneksi Neo4j"""
    NEO4J_URI = "neo4j+s://e4d78cf5.databases.neo4j.io"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "fneMq077AlzF6eFyYsN0ib4ozV54QxyVNitjXx7unIc"
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        return driver
    except Exception as e:
        st.error(f"Error connecting to Neo4j: {e}")
        return None

def init_mongodb_connection():
    """Inisialisasi koneksi MongoDB"""
    MONGO_URI = "mongodb+srv://mongodb:akuvalent@cluster0.zq9clry.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_db = mongo_client["ticketing"]
        return mongo_client, mongo_db
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {e}")
        return None, None

# ----------------------------------------
# FUNGSI QUERY DATABASE
# ----------------------------------------
def get_total_sales_period(orders_collection, start_date, end_date):
    """Hitung total penjualan dalam periode tertentu"""
    pipeline_total_sales = [
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
                "_id": None,
                "totalPenjualan": { "$sum": "$total_price" },
                "totalOrders": { "$sum": 1 }
            }
        }
    ]
    
    start_time = time.time()
    res_total = list(orders_collection.aggregate(pipeline_total_sales))
    end_time = time.time()
    
    if res_total:
        total_penjualan = res_total[0]["totalPenjualan"]
        total_orders = res_total[0]["totalOrders"]
    else:
        total_penjualan = 0
        total_orders = 0
    
    duration = end_time - start_time
    
    return total_penjualan, total_orders, duration

def get_longest_routes(driver, limit=50):
    """Ambil rute terjauh dari Neo4j"""
    def query_func(tx):
        query = """
        MATCH (a:Airport)-[r:CONNECTED_TO]->(b:Airport)
        RETURN
            a.airport_code AS origin,
            b.airport_code AS destination,
            r.distance_km AS distance_km,
            r.flight_time_hr AS flight_time_hr
        ORDER BY r.distance_km DESC
        LIMIT $limit
        """
        return list(tx.run(query, limit=limit))
    
    start_time = time.time()
    with driver.session() as session:
        records = session.execute_read(query_func)
    end_time = time.time()
    
    df_routes = pd.DataFrame([
        {
            "origin": rec["origin"],
            "destination": rec["destination"],
            "distance_km": rec["distance_km"],
            "flight_time_hr": rec["flight_time_hr"]
        }
        for rec in records
    ])
    
    duration = end_time - start_time
    return df_routes, duration

def get_sales_by_routes(orders_collection, origin_list, destination_list, start_date, end_date):
    """Hitung penjualan per rute"""
    pipeline_batch = [
        {
            "$match": {
                "depart_date": {
                    "$gte": start_date,
                    "$lte": end_date
                },
                "origin": { "$in": origin_list },
                "destination": { "$in": destination_list }
            }
        },
        {
            "$group": {
                "_id": {
                    "origin": "$origin",
                    "destination": "$destination"
                },
                "total_penjualan_rute": { "$sum": "$total_price" },
                "jumlah_order_rute": { "$sum": 1 }
            }
        }
    ]
    
    start_time = time.time()
    res_batch = list(orders_collection.aggregate(pipeline_batch))
    end_time = time.time()
    
    df_batch = pd.DataFrame([{
        "origin": doc["_id"]["origin"],
        "destination": doc["_id"]["destination"],
        "total_penjualan_rute": doc["total_penjualan_rute"],
        "jumlah_order_rute": doc["jumlah_order_rute"]
    } for doc in res_batch])
    
    duration = end_time - start_time
    return df_batch, duration

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
# MAIN APP
# ----------------------------------------
def main():
    st.title("✈️ Analisis Penjualan Tiket")
    st.markdown("---")
    
    # Sidebar untuk konfigurasi
    st.sidebar.header("⚙️ Konfigurasi")
    
    # Input tanggal custom
    st.sidebar.subheader("📅 Pilih Periode Analisis")
    
    # Preset periode
    preset_option = st.sidebar.selectbox(
        "Pilih Preset Periode:",
        ["Custom", "Ramadhan 2023", "Bulan Ini", "3 Bulan Terakhir", "Tahun Ini"]
    )
    
    # Set default dates berdasarkan preset
    if preset_option == "Ramadhan 2023":
        default_start = date(2023, 3, 10)
        default_end = date(2023, 4, 9)
    elif preset_option == "Bulan Ini":
        today = date.today()
        default_start = date(today.year, today.month, 1)
        default_end = today
    elif preset_option == "3 Bulan Terakhir":
        today = date.today()
        if today.month >= 3:
            default_start = date(today.year, today.month - 2, 1)
        else:
            default_start = date(today.year - 1, today.month + 10, 1)
        default_end = today
    elif preset_option == "Tahun Ini":
        today = date.today()
        default_start = date(today.year, 1, 1)
        default_end = today
    else:  # Custom
        default_start = date(2023, 3, 10)
        default_end = date(2023, 4, 9)
    
    # Input tanggal
    start_date = st.sidebar.date_input(
        "Tanggal Mulai",
        value=default_start,
        help="Pilih tanggal mulai periode analisis"
    )
    end_date = st.sidebar.date_input(
        "Tanggal Selesai",
        value=default_end,
        help="Pilih tanggal akhir periode analisis"
    )
    
    # Validasi tanggal
    if start_date > end_date:
        st.sidebar.error("❌ Tanggal mulai tidak boleh lebih besar dari tanggal selesai!")
        st.stop()
    
    # Tampilkan durasi periode
    period_days = (end_date - start_date).days + 1
    st.sidebar.info(f"📊 Periode: {period_days} hari")
    
    # Konversi ke datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Input jumlah rute
    limit_routes = st.sidebar.slider(
        "Jumlah Rute Terjauh",
        min_value=10,
        max_value=100,
        value=50,
        step=10
    )
    
    # Tombol untuk setup index
    if st.sidebar.button("🔧 Setup Database Indexes"):
        with st.spinner("Membuat indexes..."):
            # Inisialisasi koneksi
            driver = init_neo4j_connection()
            mongo_client, mongo_db = init_mongodb_connection()
            
            # FIX: Properly check if connections are successful
            driver_ok = driver is not None
            mongo_ok = mongo_db is not None
            
            if driver_ok and mongo_ok:
                # MongoDB indexes
                if create_mongodb_indexes(mongo_db):
                    st.sidebar.success("✅ MongoDB indexes created")
                
                # Neo4j indexes
                try:
                    with driver.session() as session:
                        session.execute_write(create_neo4j_indexes)
                    st.sidebar.success("✅ Neo4j indexes created")
                except Exception as e:
                    st.sidebar.error(f"❌ Neo4j index error: {e}")
                
                # Tutup koneksi setelah setup
                if driver:
                    driver.close()
                if mongo_client:
                    mongo_client.close()
    
    # Tombol untuk menjalankan analisis
    if st.button("🚀 Jalankan Analisis", type="primary"):
        # Container untuk hasil
        results_container = st.container()
        
        with results_container:
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Inisialisasi koneksi SETELAH tombol ditekan
                status_text.text("🔌 Menghubungkan ke database...")
                progress_bar.progress(10)
                
                driver = init_neo4j_connection()
                mongo_client, mongo_db = init_mongodb_connection()
                
                # FIX: Properly check database connections
                driver_ok = driver is not None
                mongo_ok = mongo_db is not None
                
                if not driver_ok or not mongo_ok:
                    st.error("❌ Gagal terhubung ke database!")
                    st.stop()
                
                orders_collection = mongo_db["orders"]
                
                # 1. Total Penjualan Periode
                status_text.text("📦 Menghitung total penjualan periode...")
                progress_bar.progress(20)
                
                total_penjualan, total_orders, mongo_duration = get_total_sales_period(
                    orders_collection, start_datetime, end_datetime
                )
                
                # 2. Trend Harian
                status_text.text("📈 Menganalisis trend harian...")
                progress_bar.progress(40)
                df_daily, daily_duration = get_sales_by_date(
                    orders_collection, start_datetime, end_datetime
                )
                
                # 3. Rute Terjauh dari Neo4j
                status_text.text("🛫 Mengambil rute terjauh dari Neo4j...")
                progress_bar.progress(60)
                
                df_routes, neo_duration = get_longest_routes(driver, limit_routes)
                
                # 4. Penjualan per Rute
                status_text.text("📊 Menghitung penjualan per rute...")
                progress_bar.progress(80)
                
                df_sorted = pd.DataFrame()
                batch_duration = 0
                
                if not df_routes.empty:
                    origin_list = df_routes["origin"].unique().tolist()
                    destination_list = df_routes["destination"].unique().tolist()
                    
                    df_sales, batch_duration = get_sales_by_routes(
                        orders_collection, origin_list, destination_list,
                        start_datetime, end_datetime
                    )
                    
                    # 5. Gabungkan data
                    df_combined = pd.merge(
                        df_routes,
                        df_sales,
                        on=["origin", "destination"],
                        how="left"
                    )
                    
                    df_combined[["total_penjualan_rute", "jumlah_order_rute"]] = df_combined[[
                        "total_penjualan_rute", "jumlah_order_rute"
                    ]].fillna(0)
                    
                    df_sorted = df_combined.sort_values(
                        by="total_penjualan_rute",
                        ascending=False
                    )
                
                progress_bar.progress(100)
                status_text.text("✅ Analisis selesai!")
                
                # Tampilkan hasil
                st.markdown("---")
                
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "💰 Total Penjualan",
                        f"Rp {total_penjualan:,}"
                    )
                
                with col2:
                    st.metric(
                        "📦 Total Orders",
                        f"{total_orders:,}"
                    )
                
                with col3:
                    avg_order_value = total_penjualan / total_orders if total_orders > 0 else 0
                    st.metric(
                        "💳 Rata-rata per Order",
                        f"Rp {avg_order_value:,.0f}"
                    )
                
                with col4:
                    daily_avg = total_penjualan / period_days if period_days > 0 else 0
                    st.metric(
                        "📊 Rata-rata Harian",
                        f"Rp {daily_avg:,.0f}"
                    )
                
                # Performance metrics
                st.markdown("### ⚡ Performance Metrics")
                perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
                
                with perf_col1:
                    st.metric("MongoDB Query", f"{mongo_duration:.4f}s")
                with perf_col2:
                    st.metric("Daily Trend Query", f"{daily_duration:.4f}s")
                with perf_col3:
                    st.metric("Neo4j Query", f"{neo_duration:.4f}s")
                with perf_col4:
                    st.metric("Route Sales Query", f"{batch_duration:.4f}s")
                
                # Tabs untuk hasil
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📊 Ringkasan", "📈 Trend Harian", "🛫 Rute Terjauh", 
                    "💹 Penjualan per Rute", "📈 Visualisasi Rute"
                ])
                
                # Tab Ringkasan
                with tab1:
                    st.subheader("📊 Ringkasan Analisis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"""
                        **Periode Analisis:** {start_date} - {end_date} ({period_days} hari)
                        
                        **Total Penjualan:** Rp {total_penjualan:,}
                        
                        **Total Orders:** {total_orders:,}
                        
                        **Rata-rata per Order:** Rp {avg_order_value:,.0f}
                        
                        **Rata-rata Harian:** Rp {daily_avg:,.0f}
                        """)
                    
                    with col2:
                        if not df_sorted.empty:
                            top_route = df_sorted.iloc[0]
                            st.success(f"""
                            **Rute Terlaris:**
                            
                            🛫 {top_route['origin']} → {top_route['destination']}
                            
                            💰 Penjualan: Rp {top_route['total_penjualan_rute']:,.0f}
                            
                            📦 Orders: {top_route['jumlah_order_rute']:.0f}
                            
                            📏 Jarak: {top_route['distance_km']:.0f} km
                            """)
                        else:
                            performance_summary = f"""
                            **Performance Summary:**
                            
                            ⚡ MongoDB: {mongo_duration:.4f}s
                            ⚡ Daily Trend: {daily_duration:.4f}s
                            ⚡ Neo4j: {neo_duration:.4f}s
                            ⚡ Route Sales: {batch_duration:.4f}s
                            """
                            st.info(performance_summary)
                
                # Tab Trend Harian
                with tab2:
                    st.subheader("📈 Trend Penjualan Harian")
                    if not df_daily.empty:
                        # Chart trend harian
                        fig_daily = px.line(
                            df_daily,
                            x='date',
                            y='daily_sales',
                            title='Trend Penjualan Harian',
                            labels={
                                'date': 'Tanggal',
                                'daily_sales': 'Penjualan Harian (Rp)'
                            }
                        )
                        fig_daily.update_traces(line_color='#1f77b4', line_width=3)
                        st.plotly_chart(fig_daily, use_container_width=True)
                        
                        # Tabel data harian
                        st.subheader("📊 Data Harian")
                        st.dataframe(
                            df_daily,
                            use_container_width=True,
                            column_config={
                                "date": st.column_config.DateColumn("Tanggal"),
                                "daily_sales": st.column_config.NumberColumn(
                                    "Penjualan Harian",
                                    format="Rp %.0f"
                                ),
                                "daily_orders": st.column_config.NumberColumn(
                                    "Orders Harian",
                                    format="%.0f"
                                )
                            }
                        )
                    else:
                        st.warning("Tidak ada data penjualan harian untuk periode ini.")
                
                # Tab Rute Terjauh
                with tab3:
                    st.subheader("🛫 Top Rute Terjauh")
                    if not df_routes.empty:
                        st.dataframe(
                            df_routes,
                            use_container_width=True,
                            column_config={
                                "distance_km": st.column_config.NumberColumn(
                                    "Jarak (km)",
                                    format="%.0f"
                                ),
                                "flight_time_hr": st.column_config.NumberColumn(
                                    "Waktu Terbang (jam)",
                                    format="%.2f"
                                )
                            }
                        )
                    else:
                        st.warning("Tidak ada data rute ditemukan.")
                
                # Tab Penjualan per Rute
                with tab4:
                    st.subheader("💹 Penjualan per Rute (Diurutkan)")
                    if not df_sorted.empty:
                        st.dataframe(
                            df_sorted,
                            use_container_width=True,
                            column_config={
                                "distance_km": st.column_config.NumberColumn(
                                    "Jarak (km)",
                                    format="%.0f"
                                ),
                                "flight_time_hr": st.column_config.NumberColumn(
                                    "Waktu Terbang (jam)",
                                    format="%.2f"
                                ),
                                "total_penjualan_rute": st.column_config.NumberColumn(
                                    "Total Penjualan",
                                    format="Rp %.0f"
                                ),
                                "jumlah_order_rute": st.column_config.NumberColumn(
                                    "Jumlah Order",
                                    format="%.0f"
                                )
                            }
                        )
                    else:
                        st.warning("Tidak ada data penjualan ditemukan.")
                
                # Tab Visualisasi Rute
                with tab5:
                    st.subheader("📈 Visualisasi Data Rute")
                    
                    if not df_sorted.empty:
                        # Filter data yang memiliki penjualan
                        df_viz = df_sorted[df_sorted['total_penjualan_rute'] > 0].head(20)
                        
                        if not df_viz.empty:
                            # Chart 1: Bar chart penjualan per rute
                            fig1 = px.bar(
                                df_viz,
                                x='total_penjualan_rute',
                                y=df_viz['origin'] + ' → ' + df_viz['destination'],
                                orientation='h',
                                title='Top 20 Rute dengan Penjualan Tertinggi',
                                labels={
                                    'total_penjualan_rute': 'Total Penjualan (Rp)',
                                    'y': 'Rute'
                                }
                            )
                            fig1.update_layout(height=600)
                            st.plotly_chart(fig1, use_container_width=True)
                            
                            # Chart 2: Scatter plot jarak vs penjualan
                            fig2 = px.scatter(
                                df_viz,
                                x='distance_km',
                                y='total_penjualan_rute',
                                size='jumlah_order_rute',
                                hover_data=['origin', 'destination', 'flight_time_hr'],
                                title='Hubungan Jarak vs Penjualan',
                                labels={
                                    'distance_km': 'Jarak (km)',
                                    'total_penjualan_rute': 'Total Penjualan (Rp)',
                                    'jumlah_order_rute': 'Jumlah Order'
                                }
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            st.info("Tidak ada data penjualan untuk divisualisasikan.")
                    else:
                        st.warning("Tidak ada data untuk divisualisasikan.")
            
            except Exception as e:
                st.error(f"❌ Error saat menjalankan analisis: {str(e)}")
                st.exception(e)
            
            finally:
                # Tutup koneksi di dalam try-finally block
                try:
                    if 'driver' in locals() and driver:
                        driver.close()
                    if 'mongo_client' in locals() and mongo_client:
                        mongo_client.close()
                except Exception as close_error:
                    st.warning(f"Warning saat menutup koneksi: {close_error}")

if __name__ == "__main__":
    main()
