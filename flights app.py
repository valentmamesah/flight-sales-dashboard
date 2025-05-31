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
    page_title="Analisis Penjualan Tiket Ramadhan",
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
@st.cache_resource
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

@st.cache_resource
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
def get_total_sales_ramadhan(orders_collection, start_date, end_date):
    """Hitung total penjualan selama Ramadhan"""
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
                "totalPenjualan": { "$sum": "$total_price" }
            }
        }
    ]
    
    start_time = time.time()
    res_total = list(orders_collection.aggregate(pipeline_total_sales))
    end_time = time.time()
    
    total_penjualan = res_total[0]["totalPenjualan"] if res_total else 0
    duration = end_time - start_time
    
    return total_penjualan, duration

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

# ----------------------------------------
# MAIN APP
# ----------------------------------------
def main():
    st.title("✈️ Analisis Penjualan Tiket Ramadhan")
    st.markdown("---")
    
    # Sidebar untuk konfigurasi
    st.sidebar.header("⚙️ Konfigurasi")
    
    # Input tanggal Ramadhan
    st.sidebar.subheader("📅 Rentang Tanggal Ramadhan")
    start_date = st.sidebar.date_input(
        "Tanggal Mulai",
        value=date(2023, 3, 10)
    )
    end_date = st.sidebar.date_input(
        "Tanggal Selesai",
        value=date(2023, 4, 9)
    )
    
    # Konversi ke datetime
    start_ramadhan = datetime.combine(start_date, datetime.min.time())
    end_ramadhan = datetime.combine(end_date, datetime.max.time())
    
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
            
            if driver and mongo_db:
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
    
    # Tombol untuk menjalankan analisis
    if st.button("🚀 Jalankan Analisis", type="primary"):
        # Inisialisasi koneksi
        driver = init_neo4j_connection()
        mongo_client, mongo_db = init_mongodb_connection()
        
        if not driver or not mongo_db:
            st.error("❌ Gagal terhubung ke database!")
            return
        
        orders_collection = mongo_db["orders"]
        
        # Container untuk hasil
        results_container = st.container()
        
        with results_container:
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1. Total Penjualan Ramadhan
            status_text.text("📦 Menghitung total penjualan Ramadhan...")
            progress_bar.progress(25)
            
            total_penjualan, mongo_duration = get_total_sales_ramadhan(
                orders_collection, start_ramadhan, end_ramadhan
            )
            
            # 2. Rute Terjauh dari Neo4j
            status_text.text("🛫 Mengambil rute terjauh dari Neo4j...")
            progress_bar.progress(50)
            
            df_routes, neo_duration = get_longest_routes(driver, limit_routes)
            
            # 3. Penjualan per Rute
            status_text.text("📊 Menghitung penjualan per rute...")
            progress_bar.progress(75)
            
            if not df_routes.empty:
                origin_list = df_routes["origin"].unique().tolist()
                destination_list = df_routes["destination"].unique().tolist()
                
                df_sales, batch_duration = get_sales_by_routes(
                    orders_collection, origin_list, destination_list,
                    start_ramadhan, end_ramadhan
                )
                
                # 4. Gabungkan data
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
            else:
                df_sorted = pd.DataFrame()
                batch_duration = 0
            
            progress_bar.progress(100)
            status_text.text("✅ Analisis selesai!")
            
            # Tampilkan hasil
            st.markdown("---")
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "💰 Total Penjualan Ramadhan",
                    f"Rp {total_penjualan:,}"
                )
            
            with col2:
                st.metric(
                    "⏱️ Waktu Query MongoDB",
                    f"{mongo_duration:.4f} detik"
                )
            
            with col3:
                st.metric(
                    "⏱️ Waktu Query Neo4j",
                    f"{neo_duration:.4f} detik"
                )
            
            with col4:
                st.metric(
                    "🛣️ Jumlah Rute Ditemukan",
                    len(df_routes)
                )
            
            # Tabs untuk hasil
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Ringkasan", "🛫 Rute Terjauh", "💹 Penjualan per Rute", "📈 Visualisasi"
            ])
            
            with tab1:
                st.subheader("📊 Ringkasan Analisis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"""
                    **Period Analisis:** {start_date} - {end_date}
                    
                    **Total Penjualan:** Rp {total_penjualan:,}
                    
                    **Jumlah Rute Terjauh:** {len(df_routes)}
                    
                    **Performance:**
                    - MongoDB Query: {mongo_duration:.4f}s
                    - Neo4j Query: {neo_duration:.4f}s
                    - Batch Query: {batch_duration:.4f}s
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
            
            with tab2:
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
            
            with tab3:
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
            
            with tab4:
                st.subheader("📈 Visualisasi Data")
                
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
        
        # Tutup koneksi
        driver.close()
        mongo_client.close()

if __name__ == "__main__":
    main()