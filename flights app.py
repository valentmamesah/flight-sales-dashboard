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
    st.title("Analisis Penjualan Tiket")
    
    # Input periode analisis
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Tanggal Mulai",
            value=date(2023, 3, 10)
        )
    
    with col2:
        end_date = st.date_input(
            "Tanggal Selesai",
            value=date(2023, 4, 9)
        )
    
    # Validasi tanggal
    if start_date > end_date:
        st.error("Tanggal mulai tidak boleh lebih besar dari tanggal selesai!")
        return
    
    # Konversi ke datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Tombol untuk menjalankan analisis
    if st.button("Jalankan Analisis", type="primary"):
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
            with st.spinner("Memproses data..."):
                # Total Penjualan Periode
                total_penjualan, total_orders, mongo_duration = get_total_sales_period(
                    orders_collection, start_datetime, end_datetime
                )
                
                # Rute Terjauh dari Neo4j
                df_routes, neo_duration = get_longest_routes(driver, 50)
                
                # Penjualan per Rute
                df_sorted = pd.DataFrame()
                if not df_routes.empty:
                    origin_list = df_routes["origin"].unique().tolist()
                    destination_list = df_routes["destination"].unique().tolist()
                    
                    df_sales, batch_duration = get_sales_by_routes(
                        orders_collection, origin_list, destination_list,
                        start_datetime, end_datetime
                    )
                    
                    # Gabungkan data
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
            
            # Tampilkan hasil
            st.markdown("---")
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Total Penjualan",
                    f"Rp {total_penjualan:,}"
                )
            
            with col2:
                st.metric(
                    "Total Orders",
                    f"{total_orders:,}"
                )
            
            with col3:
                avg_order_value = total_penjualan / total_orders if total_orders > 0 else 0
                st.metric(
                    "Rata-rata per Order",
                    f"Rp {avg_order_value:,.0f}"
                )
            
            # Tampilkan data
            if not df_sorted.empty:
                st.subheader("Penjualan per Rute")
                
                # Top 5 rute terlaris
                top_routes = df_sorted[df_sorted['total_penjualan_rute'] > 0].head(5)
                if not top_routes.empty:
                    st.write("**Top 5 Rute Terlaris:**")
                    for idx, row in top_routes.iterrows():
                        st.write(f"• {row['origin']} → {row['destination']}: Rp {row['total_penjualan_rute']:,.0f} ({row['jumlah_order_rute']:.0f} orders)")
                
                # Tabel lengkap
                with st.expander("Lihat Semua Data Rute"):
                    st.dataframe(
                        df_sorted,
                        use_container_width=True,
                        column_config={
                            "origin": "Asal",
                            "destination": "Tujuan",
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
        
        # Tutup koneksi
        driver.close()
        mongo_client.close()

if __name__ == "__main__":
    main()
