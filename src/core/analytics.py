"""
Analytics module
Handles data analysis queries and business insights generation
"""

import time
import pandas as pd
import streamlit as st


def get_sales_by_date(orders_collection, start_date, end_date):
    """
    Calculate daily sales aggregates within a specified date range
    
    Args:
        orders_collection: MongoDB orders collection
        start_date: Start date (datetime object)
        end_date: End date (datetime object)
        
    Returns:
        tuple: (DataFrame with daily sales, query execution time in seconds)
    """
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
                "daily_sales": {"$sum": "$total_price"},
                "daily_orders": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    
    start_time = time.time()
    res_daily = list(orders_collection.aggregate(pipeline_daily))
    execution_time = time.time() - start_time
    
    df_daily = pd.DataFrame([{
        "date": doc["_id"],
        "daily_sales": doc["daily_sales"],
        "daily_orders": doc["daily_orders"]
    } for doc in res_daily])
    
    if not df_daily.empty:
        df_daily['date'] = pd.to_datetime(df_daily['date'])
    
    return df_daily, execution_time


def run_scenario_without_optimization(orders_collection, driver, start_date, end_date):
    """
    Execute analysis queries without database indexing and optimization
    Uses individual queries for each route instead of batch processing
    
    Args:
        orders_collection: MongoDB orders collection
        driver: Neo4j driver instance
        start_date: Start date (datetime object)
        end_date: End date (datetime object)
        
    Returns:
        dict: Results including metrics, dataframes, and query execution times
    """
    results = {}
    
    # 1. Calculate Total Sales
    pipeline_total = [
        {"$match": {"depart_date": {"$gte": start_date, "$lte": end_date}}},
        {
            "$group": {
                "_id": None,
                "total_sales": {"$sum": "$total_price"},
                "total_orders": {"$sum": 1}
            }
        }
    ]
    
    start_time = time.time()
    res_total = list(orders_collection.aggregate(pipeline_total))
    results['mongo_total_time'] = time.time() - start_time
    
    results['total_sales'] = res_total[0]["total_sales"] if res_total else 0
    results['total_orders'] = res_total[0]["total_orders"] if res_total else 0
    
    # 2. Fetch Daily Trend
    df_daily, daily_time = get_sales_by_date(orders_collection, start_date, end_date)
    results['daily_trend_time'] = daily_time
    results['df_daily'] = df_daily
    
    # 3. Fetch Routes from Neo4j
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
        "origin": rec["origin"],
        "destination": rec["destination"],
        "distance_km": rec["distance_km"],
        "flight_time_hr": rec["flight_time_hr"]
    } for rec in route_records])
    
    # 4. Calculate Route Sales (Individual Queries - INEFFICIENT)
    start_time = time.time()
    route_sales = []
    
    for _, row in df_routes.iterrows():
        pipeline_route = [
            {
                "$match": {
                    "origin": row["origin"],
                    "destination": row["destination"],
                    "depart_date": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_sales": {"$sum": "$total_price"},
                    "total_orders": {"$sum": 1}
                }
            }
        ]
        
        res_route = list(orders_collection.aggregate(pipeline_route))
        if res_route:
            route_sales.append({
                "origin": row["origin"],
                "destination": row["destination"],
                "total_sales": res_route[0]["total_sales"],
                "total_orders": res_route[0]["total_orders"]
            })
        else:
            route_sales.append({
                "origin": row["origin"],
                "destination": row["destination"],
                "total_sales": 0,
                "total_orders": 0
            })
    
    results['mongo_routes_time'] = time.time() - start_time
    
    # 5. Merge data
    df_sales = pd.DataFrame(route_sales)
    df_combined = pd.merge(df_routes, df_sales, on=["origin", "destination"], how="left")
    df_combined[["total_sales", "total_orders"]] = \
        df_combined[["total_sales", "total_orders"]].fillna(0)
    results['df_sorted'] = df_combined.sort_values(by="total_sales", ascending=False)
    
    return results


def run_scenario_with_optimization(orders_collection, driver, start_date, end_date):
    """
    Execute analysis queries with database indexing and optimization
    Uses batch processing instead of individual queries
    
    Args:
        orders_collection: MongoDB orders collection
        driver: Neo4j driver instance
        start_date: Start date (datetime object)
        end_date: End date (datetime object)
        
    Returns:
        dict: Results including metrics, dataframes, and query execution times
    """
    results = {}
    
    # 1. Calculate Total Sales
    pipeline_total = [
        {"$match": {"depart_date": {"$gte": start_date, "$lte": end_date}}},
        {
            "$group": {
                "_id": None,
                "total_sales": {"$sum": "$total_price"},
                "total_orders": {"$sum": 1}
            }
        }
    ]
    
    start_time = time.time()
    res_total = list(orders_collection.aggregate(pipeline_total))
    results['mongo_total_time'] = time.time() - start_time
    
    results['total_sales'] = res_total[0]["total_sales"] if res_total else 0
    results['total_orders'] = res_total[0]["total_orders"] if res_total else 0
    
    # 2. Fetch Daily Trend
    df_daily, daily_time = get_sales_by_date(orders_collection, start_date, end_date)
    results['daily_trend_time'] = daily_time
    results['df_daily'] = df_daily
    
    # 3. Fetch Routes from Neo4j (with optimized query)
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
        "origin": rec["origin"],
        "destination": rec["destination"],
        "distance_km": rec["distance_km"],
        "flight_time_hr": rec["flight_time_hr"]
    } for rec in route_records])
    
    # 4. Calculate Route Sales (Batch Query - OPTIMIZED)
    start_time = time.time()
    origin_list = df_routes["origin"].unique().tolist()
    destination_list = df_routes["destination"].unique().tolist()
    
    # Single batch query instead of N individual queries
    pipeline_batch = [
        {
            "$match": {
                "depart_date": {"$gte": start_date, "$lte": end_date},
                "origin": {"$in": origin_list},
                "destination": {"$in": destination_list}
            }
        },
        {
            "$group": {
                "_id": {"origin": "$origin", "destination": "$destination"},
                "total_sales": {"$sum": "$total_price"},
                "total_orders": {"$sum": 1}
            }
        }
    ]
    
    res_batch = list(orders_collection.aggregate(pipeline_batch))
    results['mongo_routes_time'] = time.time() - start_time
    
    df_batch = pd.DataFrame([{
        "origin": doc["_id"]["origin"],
        "destination": doc["_id"]["destination"],
        "total_sales": doc["total_sales"],
        "total_orders": doc["total_orders"]
    } for doc in res_batch])
    
    # 5. Merge data
    df_combined = pd.merge(df_routes, df_batch, on=["origin", "destination"], how="left")
    df_combined[["total_sales", "total_orders"]] = \
        df_combined[["total_sales", "total_orders"]].fillna(0)
    results['df_sorted'] = df_combined.sort_values(by="total_sales", ascending=False)
    
    return results


def generate_insights(results1, results2, period_days):
    """
    Generate business insights from analysis results
    
    Args:
        results1: Results from scenario without optimization
        results2: Results from scenario with optimization
        period_days: Number of days in analysis period
        
    Returns:
        list: List of insight dictionaries with type, title, and content
    """
    insights = []
    
    # Data from optimized results
    total_sales = results2['total_sales']
    total_orders = results2['total_orders']
    df_daily = results2['df_daily']
    df_sorted = results2['df_sorted']
    
    # 1. Performance Impact Insight
    if 'total_time1' in st.session_state and 'total_time2' in st.session_state:
        time1 = st.session_state['total_time1']
        time2 = st.session_state['total_time2']
        improvement = ((time1 - time2) / time1) * 100
        insights.append({
            "type": "performance",
            "title": "Performance Optimization Impact",
            "content": f"Optimization improves performance by {improvement:.1f}% from {time1:.2f}s to {time2:.2f}s. "
                      f"This demonstrates the importance of indexing and batch query processing."
        })
    
    # 2. Sales Performance Insight
    avg_daily = total_sales / period_days if period_days > 0 else 0
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    insights.append({
        "type": "sales",
        "title": "Sales Performance Overview",
        "content": f"During {period_days} days, {total_orders:,} transactions occurred with total sales of Rp {total_sales:,}. "
                  f"Average order value: Rp {avg_order_value:,.0f}, Average daily sales: Rp {avg_daily:,.0f}."
    })
    
    # 3. Daily Trend Insight
    if not df_daily.empty:
        max_day = df_daily.loc[df_daily['daily_sales'].idxmax()]
        min_day = df_daily.loc[df_daily['daily_sales'].idxmin()]
        
        insights.append({
            "type": "trend",
            "title": "Daily Sales Trend Analysis",
            "content": f"Highest sales on {max_day['date'].strftime('%d %B %Y')}: Rp {max_day['daily_sales']:,.0f}. "
                      f"Lowest sales on {min_day['date'].strftime('%d %B %Y')}: Rp {min_day['daily_sales']:,.0f}."
        })
    
    # 4. Route Performance Insight
    if not df_sorted.empty:
        top_routes = df_sorted[df_sorted['total_sales'] > 0].head(5)
        if not top_routes.empty:
            top_route = top_routes.iloc[0]
            total_route_sales = top_routes['total_sales'].sum()
            route_contribution = (total_route_sales / total_sales) * 100
            
            insights.append({
                "type": "route",
                "title": "Route Performance Analysis",
                "content": f"Best-selling route: {top_route['origin']} to {top_route['destination']} "
                          f"with sales of Rp {top_route['total_sales']:,.0f} ({int(top_route['total_orders'])} orders). "
                          f"Top 5 routes contribute {route_contribution:.1f}% of total sales."
            })
        
        # Distance vs Sales Analysis
        routes_with_sales = df_sorted[df_sorted['total_sales'] > 0]
        if len(routes_with_sales) > 10:
            correlation = routes_with_sales['distance_km'].corr(routes_with_sales['total_sales'])
            correlation_strength = "weak" if abs(correlation) < 0.3 else "moderate" if abs(correlation) < 0.7 else "strong"
            correlation_direction = "positive" if correlation > 0 else "negative"
            
            insights.append({
                "type": "correlation",
                "title": "Distance vs Sales Correlation",
                "content": f"Distance-sales correlation: {correlation:.3f} ({correlation_strength} {correlation_direction}). "
                          f"Route distance {'has' if abs(correlation) > 0.3 else 'does not have'} significant impact on sales volume."
            })
    
    # 5. Business Recommendations
    recommendations = []
    
    if not df_daily.empty:
        low_sales_threshold = df_daily['daily_sales'].quantile(0.25)
        low_sales_days = len(df_daily[df_daily['daily_sales'] <= low_sales_threshold])
        
        if low_sales_days > 0:
            recommendations.append(f"Focus marketing strategies on {low_sales_days} low-sales days")
    
    if not df_sorted.empty:
        zero_sales_routes = len(df_sorted[df_sorted['total_sales'] == 0])
        if zero_sales_routes > 0:
            recommendations.append(f"Evaluate and optimize {zero_sales_routes} routes with zero sales")
    
    if recommendations:
        insights.append({
            "type": "recommendation",
            "title": "Business Recommendations",
            "content": "- " + "\n- ".join(recommendations)
        })
    
    return insights
