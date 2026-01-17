"""
Flight Ticket Sales & Performance Analysis Dashboard
Main Streamlit application
"""

import streamlit as st
import time
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import APP_TITLE, APP_ICON, PAGE_LAYOUT, DEFAULT_START_DATE, DEFAULT_END_DATE
from src.core.database import (
    init_connections,
    create_mongodb_indexes,
    drop_mongodb_indexes,
    create_neo4j_indexes,
    drop_neo4j_indexes
)
from src.core.analytics import (
    run_scenario_without_optimization,
    run_scenario_with_optimization,
    generate_insights
)


def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout=PAGE_LAYOUT
    )


def render_sidebar_controls(start_date, end_date):
    """
    Render sidebar controls for period selection and index management
    
    Returns:
        tuple: (start_date, end_date, period_days)
    """
    st.sidebar.header("Configuration")
    
    # Analysis Period Section
    st.sidebar.subheader("Analysis Period")
    preset = st.sidebar.selectbox(
        "Select Preset Period:",
        ["Ramadhan 2023", "Custom"]
    )
    
    if preset == "Ramadhan 2023":
        start_date = date(2023, 3, 10)
        end_date = date(2023, 4, 9)
    else:
        start_date = st.sidebar.date_input("Start Date", value=date(2023, 3, 10))
        end_date = st.sidebar.date_input("End Date", value=date(2023, 4, 9))
    
    if start_date > end_date:
        st.sidebar.error("Start date cannot be greater than end date!")
        st.stop()
    
    period_days = (end_date - start_date).days + 1
    st.sidebar.info(f"Analysis Period: {period_days} days")
    
    # Index Management Section
    st.sidebar.subheader("Index Management")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("Create Index", use_container_width=True):
            with st.spinner("Creating indexes..."):
                driver, mongo_client, mongo_db = init_connections()
                if driver and mongo_client:
                    try:
                        create_mongodb_indexes(mongo_db)
                        with driver.session() as session:
                            session.execute_write(create_neo4j_indexes)
                        st.sidebar.success("Indexes created successfully!")
                    except Exception as e:
                        st.sidebar.error(f"Error: {e}")
                    finally:
                        if driver:
                            driver.close()
                        if mongo_client:
                            mongo_client.close()
    
    with col2:
        if st.button("Drop Index", use_container_width=True):
            with st.spinner("Dropping indexes..."):
                driver, mongo_client, mongo_db = init_connections()
                if driver and mongo_client:
                    try:
                        drop_mongodb_indexes(mongo_db)
                        with driver.session() as session:
                            session.execute_write(drop_neo4j_indexes)
                        st.sidebar.success("Indexes dropped successfully!")
                    except Exception as e:
                        st.sidebar.error(f"Error: {e}")
                    finally:
                        if driver:
                            driver.close()
                        if mongo_client:
                            mongo_client.close()
    
    return start_date, end_date, period_days


def render_tab_scenario_1(start_datetime, end_datetime):
    """Render tab for scenario without optimization"""
    st.header("Scenario 1: Without Indexing & Optimization")
    
    if st.button("Run Scenario 1", key="scenario1"):
        with st.spinner("Running analysis without optimization..."):
            total_start = time.time()
            
            driver, mongo_client, mongo_db = init_connections()
            if not driver or not mongo_client:
                st.error("Failed to connect to databases!")
                return
            
            try:
                orders_collection = mongo_db["orders"]
                results1 = run_scenario_without_optimization(
                    orders_collection, driver, start_datetime, end_datetime
                )
                total_time1 = time.time() - total_start
                
                st.session_state['results1'] = results1
                st.session_state['total_time1'] = total_time1
                
            finally:
                if driver:
                    driver.close()
                if mongo_client:
                    mongo_client.close()
    
    # Display results if available
    if 'results1' in st.session_state:
        results = st.session_state['results1']
        total_time = st.session_state['total_time1']
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Sales", f"Rp {results['total_sales']:,}")
        with col2:
            st.metric("Total Orders", f"{results['total_orders']:,}")
        with col3:
            avg_order = (results['total_sales'] / results['total_orders']
                        if results['total_orders'] > 0 else 0)
            st.metric("Average Order Value", f"Rp {avg_order:,.0f}")
        with col4:
            st.metric("Total Time", f"{total_time:.2f}s")
        
        # Performance breakdown
        st.subheader("Performance Breakdown")
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
        st.subheader("Top 10 Best-Selling Routes")
        top_routes = results['df_sorted'][results['df_sorted']['total_sales'] > 0].head(10)
        if not top_routes.empty:
            st.dataframe(
                top_routes[['origin', 'destination', 'distance_km',
                           'total_sales', 'total_orders']],
                use_container_width=True,
                column_config={
                    "distance_km": st.column_config.NumberColumn("Distance (km)", format="%.0f"),
                    "total_sales": st.column_config.NumberColumn("Sales", format="Rp %.0f"),
                    "total_orders": st.column_config.NumberColumn("Orders", format="%.0f")
                }
            )


def render_tab_scenario_2(start_datetime, end_datetime):
    """Render tab for scenario with optimization"""
    st.header("Scenario 2: With Indexing & Optimization")
    
    if st.button("Run Scenario 2", key="scenario2"):
        with st.spinner("Running analysis with optimization..."):
            total_start = time.time()
            
            driver, mongo_client, mongo_db = init_connections()
            if not driver or not mongo_client:
                st.error("Failed to connect to databases!")
                return
            
            try:
                orders_collection = mongo_db["orders"]
                results2 = run_scenario_with_optimization(
                    orders_collection, driver, start_datetime, end_datetime
                )
                total_time2 = time.time() - total_start
                
                st.session_state['results2'] = results2
                st.session_state['total_time2'] = total_time2
                
            finally:
                if driver:
                    driver.close()
                if mongo_client:
                    mongo_client.close()
    
    # Display results if available
    if 'results2' in st.session_state:
        results = st.session_state['results2']
        total_time = st.session_state['total_time2']
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Sales", f"Rp {results['total_sales']:,}")
        with col2:
            st.metric("Total Orders", f"{results['total_orders']:,}")
        with col3:
            avg_order = (results['total_sales'] / results['total_orders']
                        if results['total_orders'] > 0 else 0)
            st.metric("Average Order Value", f"Rp {avg_order:,.0f}")
        with col4:
            st.metric("Total Time", f"{total_time:.2f}s")
        
        # Performance breakdown
        st.subheader("Performance Breakdown")
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
        st.subheader("Top 10 Best-Selling Routes")
        top_routes = results['df_sorted'][results['df_sorted']['total_sales'] > 0].head(10)
        if not top_routes.empty:
            st.dataframe(
                top_routes[['origin', 'destination', 'distance_km',
                           'total_sales', 'total_orders']],
                use_container_width=True,
                column_config={
                    "distance_km": st.column_config.NumberColumn("Distance (km)", format="%.0f"),
                    "total_sales": st.column_config.NumberColumn("Sales", format="Rp %.0f"),
                    "total_orders": st.column_config.NumberColumn("Orders", format="%.0f")
                }
            )


def render_tab_performance_comparison():
    """Render tab for performance comparison between scenarios"""
    st.header("Database Performance Comparison")
    
    if 'results1' in st.session_state and 'results2' in st.session_state:
        time1 = st.session_state['total_time1']
        time2 = st.session_state['total_time2']
        improvement = ((time1 - time2) / time1) * 100
        speedup = time1 / time2 if time2 > 0 else 0
        
        # Performance comparison metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Without Optimization", f"{time1:.2f}s")
        with col2:
            st.metric("With Optimization", f"{time2:.2f}s")
        with col3:
            st.metric("Performance Improvement", f"{improvement:.1f}%")
        with col4:
            st.metric("Speedup Factor", f"{speedup:.1f}x")
        
        # Detailed performance breakdown
        st.subheader("Detailed Performance Breakdown")
        
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
            "Without Optimization (s)": [
                results1['mongo_total_time'],
                results1['daily_trend_time'],
                results1['neo4j_time'],
                results1['mongo_routes_time'],
                time1
            ],
            "With Optimization (s)": [
                results2['mongo_total_time'],
                results2['daily_trend_time'],
                results2['neo4j_time'],
                results2['mongo_routes_time'],
                time2
            ]
        }
        
        df_perf = pd.DataFrame(perf_data)
        df_perf["Improvement (%)"] = (
            (df_perf["Without Optimization (s)"] - df_perf["With Optimization (s)"]) /
            df_perf["Without Optimization (s)"]
        ) * 100
        df_perf["Speedup"] = (df_perf["Without Optimization (s)"] /
                             df_perf["With Optimization (s)"])
        
        st.dataframe(
            df_perf,
            use_container_width=True,
            column_config={
                "Without Optimization (s)": st.column_config.NumberColumn(
                    "Without Optimization (s)", format="%.4f"
                ),
                "With Optimization (s)": st.column_config.NumberColumn(
                    "With Optimization (s)", format="%.4f"
                ),
                "Improvement (%)": st.column_config.NumberColumn(
                    "Improvement (%)", format="%.1f"
                ),
                "Speedup": st.column_config.NumberColumn("Speedup", format="%.1f")
            }
        )
        
        # Performance visualization
        st.subheader("Performance Comparison Chart")
        
        fig_perf = go.Figure()
        
        fig_perf.add_trace(go.Bar(
            name='Without Optimization',
            x=df_perf["Query Type"][:-1],
            y=df_perf["Without Optimization (s)"][:-1],
            marker_color='#ff6b6b'
        ))
        
        fig_perf.add_trace(go.Bar(
            name='With Optimization',
            x=df_perf["Query Type"][:-1],
            y=df_perf["With Optimization (s)"][:-1],
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
        st.subheader("Key Performance Insights")
        
        biggest_improvement_idx = df_perf["Improvement (%)"][:-1].idxmax()
        biggest_improvement = df_perf.iloc[biggest_improvement_idx]
        
        insight_text = f"""
        **Key Findings:**
        
        - **Overall Performance Gain**: Optimization improved performance by {improvement:.1f}% ({speedup:.1f}x speedup)
        
        - **Most Impacted Query**: {biggest_improvement['Query Type']} showed the largest improvement ({biggest_improvement['Improvement (%)']:.1f}%)
        
        - **Batch Processing Impact**: Converting individual route queries to batch processing significantly reduced execution time
        
        - **Index Benefits**: Database indexes greatly accelerate filtering and sorting operations
        """
        
        st.info(insight_text)
        
    else:
        st.warning("Run both scenarios first to see performance comparison!")


def render_tab_business_insights(period_days, start_date, end_date):
    """Render tab for business insights and analytics"""
    st.header("Business Insights & Advanced Analytics")
    
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
        st.subheader("Route Efficiency Analysis")
        
        df_sorted = results2['df_sorted']
        df_daily = results2['df_daily']
        
        if not df_sorted.empty and not df_daily.empty:
            routes_with_sales = df_sorted[df_sorted['total_sales'] > 0].copy()
            if not routes_with_sales.empty:
                routes_with_sales['revenue_per_km'] = (
                    routes_with_sales['total_sales'] / routes_with_sales['distance_km']
                )
                routes_with_sales['revenue_per_hour'] = (
                    routes_with_sales['total_sales'] / routes_with_sales['flight_time_hr']
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Most Efficient Routes (Revenue per km)")
                    top_efficient_km = routes_with_sales.nlargest(5, 'revenue_per_km')[
                        ['origin', 'destination', 'distance_km', 'total_sales', 'revenue_per_km']
                    ]
                    st.dataframe(
                        top_efficient_km,
                        use_container_width=True,
                        column_config={
                            "revenue_per_km": st.column_config.NumberColumn("Revenue/km", format="Rp %.0f")
                        }
                    )
                
                with col2:
                    st.subheader("Most Efficient Routes (Revenue per hour)")
                    top_efficient_hr = routes_with_sales.nlargest(5, 'revenue_per_hour')[
                        ['origin', 'destination', 'flight_time_hr', 'total_sales', 'revenue_per_hour']
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
                st.subheader("Daily Sales Statistics")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Highest Daily Sales", f"Rp {df_daily['daily_sales'].max():,.0f}")
                with col2:
                    st.metric("Lowest Daily Sales", f"Rp {df_daily['daily_sales'].min():,.0f}")
                with col3:
                    st.metric("Average Daily Sales", f"Rp {df_daily['daily_sales'].mean():,.0f}")
                with col4:
                    std_dev = df_daily['daily_sales'].std()
                    st.metric("Standard Deviation", f"Rp {std_dev:,.0f}")
    
    else:
        st.warning("Run the optimization scenario first to see business insights!")


def render_tab_data_visualization(start_date, end_date):
    """Render tab for data visualization and charts"""
    st.header("Data Visualization & Dashboard")
    
    if 'results2' in st.session_state:
        results = st.session_state['results2']
        df_daily = results['df_daily']
        df_sorted = results['df_sorted']
        
        # Daily sales trend
        if not df_daily.empty:
            st.subheader("Daily Sales Trend")
            
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
            
            # Orders vs Sales comparison
            fig_orders = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Daily Sales', 'Daily Orders'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            fig_orders.add_trace(
                go.Scatter(
                    x=df_daily['date'],
                    y=df_daily['daily_sales'],
                    mode='lines+markers',
                    name='Sales',
                    line=dict(color='#1f77b4')
                ),
                row=1, col=1
            )
            
            fig_orders.add_trace(
                go.Scatter(
                    x=df_daily['date'],
                    y=df_daily['daily_orders'],
                    mode='lines+markers',
                    name='Orders',
                    line=dict(color='#ff7f0e')
                ),
                row=1, col=2
            )
            
            fig_orders.update_layout(height=400, title_text="Daily Sales vs Orders")
            st.plotly_chart(fig_orders, use_container_width=True)
        
        # Route analysis visualizations
        if not df_sorted.empty:
            routes_with_sales = df_sorted[df_sorted['total_sales'] > 0]
            
            if not routes_with_sales.empty:
                st.subheader("Route Analysis Visualizations")
                
                # Top routes bar chart
                top_10_routes = routes_with_sales.head(10)
                top_10_routes_copy = top_10_routes.copy()
                top_10_routes_copy['route'] = (
                    top_10_routes_copy['origin'] + ' to ' + top_10_routes_copy['destination']
                )
                
                fig_routes = px.bar(
                    top_10_routes_copy,
                    x='total_sales',
                    y='route',
                    orientation='h',
                    title="Top 10 Routes by Sales Revenue",
                    labels={'total_sales': 'Sales Revenue (Rp)', 'route': 'Route'}
                )
                fig_routes.update_layout(height=500)
                st.plotly_chart(fig_routes, use_container_width=True)
                
                # Distance vs Sales scatter plot
                fig_scatter = px.scatter(
                    routes_with_sales,
                    x='distance_km',
                    y='total_sales',
                    size='total_orders',
                    hover_data=['origin', 'destination', 'flight_time_hr'],
                    title="Route Distance vs Sales Revenue",
                    labels={
                        'distance_km': 'Distance (km)',
                        'total_sales': 'Sales Revenue (Rp)',
                        'total_orders': 'Number of Orders'
                    }
                )
                fig_scatter.update_layout(height=500)
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Sales distribution
                st.subheader("Distribution Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_hist = px.histogram(
                        routes_with_sales,
                        x='total_sales',
                        nbins=20,
                        title="Sales Revenue Distribution",
                        labels={'total_sales': 'Sales Revenue (Rp)'}
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                with col2:
                    fig_dist = px.histogram(
                        routes_with_sales,
                        x='distance_km',
                        nbins=20,
                        title="Route Distance Distribution",
                        labels={'distance_km': 'Distance (km)'}
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
                
                # Summary statistics table
                st.subheader("Summary Statistics")
                
                summary_stats = {
                    'Revenue': routes_with_sales['total_sales'].describe(),
                    'Orders': routes_with_sales['total_orders'].describe(),
                    'Distance (km)': routes_with_sales['distance_km'].describe(),
                    'Flight Time (hr)': routes_with_sales['flight_time_hr'].describe()
                }
                
                summary_df = pd.DataFrame(summary_stats).round(2)
                st.dataframe(summary_df, use_container_width=True)
    
    else:
        st.warning("Run the analysis first to see data visualizations!")


def main():
    """Main application entry point"""
    configure_page()
    
    # Header
    st.title("Flight Ticket Sales & Performance Analysis")
    st.markdown("Comprehensive analysis of flight ticket sales with database performance comparison")
    st.markdown("---")
    
    # Sidebar configuration
    start_date = date(2023, 3, 10)
    end_date = date(2023, 4, 9)
    start_date, end_date, period_days = render_sidebar_controls(start_date, end_date)
    
    # Convert to datetime objects for database queries
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Without Optimization",
        "With Optimization",
        "Performance Comparison",
        "Business Insights",
        "Data Visualization"
    ])
    
    # Render tabs
    with tab1:
        render_tab_scenario_1(start_datetime, end_datetime)
    
    with tab2:
        render_tab_scenario_2(start_datetime, end_datetime)
    
    with tab3:
        render_tab_performance_comparison()
    
    with tab4:
        render_tab_business_insights(period_days, start_date, end_date)
    
    with tab5:
        render_tab_data_visualization(start_date, end_date)
    
    # Footer
    st.markdown("---")
    st.markdown("Flight Ticket Sales Analysis Dashboard | Built with Streamlit, MongoDB & Neo4j")


if __name__ == "__main__":
    main()
