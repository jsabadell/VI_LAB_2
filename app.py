import streamlit as st
import pandas as pd
import altair as alt
import itertools

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NSF Grants Explorer",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

alt.data_transformers.enable("default")


# -----------------------------------------------------------------------------
# 2. DATA LOADING (Cached for Performance)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # Load Files
    try:
        df_grants = pd.read_csv("NSF_Grants_Last5Years_Clean.csv")
        df_trump = pd.read_csv("trump17-21-csv.csv")
        df_pop_raw = pd.read_csv("estimated_population.csv")
        df_abbr_raw = pd.read_csv("state_abbreviations.csv")
    except FileNotFoundError as e:
        st.error(
            f"File not found: {e}. Please ensure all CSVs are in the app directory."
        )
        return None, None, None, None

    # Cleaning
    df_grants.columns = df_grants.columns.str.strip()
    df_trump.columns = df_trump.columns.str.strip()

    # Ensure Year is numeric
    df_grants["year"] = (
        pd.to_numeric(df_grants["year"], errors="coerce").fillna(0).astype(int)
    )

    # --- PREP POPULATION DATA (Q6) ---
    df_pop_raw.columns = df_pop_raw.columns.str.strip()
    df_abbr_raw.columns = df_abbr_raw.columns.str.strip()

    pop_cols = [c for c in df_pop_raw.columns if c.lower().startswith("pop_")]
    df_pop_long = df_pop_raw.melt(
        id_vars=["state"], value_vars=pop_cols, var_name="year", value_name="population"
    )
    df_pop_long["year"] = (
        df_pop_long["year"].str.replace("pop_", "", regex=False).astype(int)
    )
    df_pop_long["population"] = pd.to_numeric(
        df_pop_long["population"], errors="coerce"
    )

    # Filter Pop years to match relevant data range (2020-2024)
    df_pop_long = df_pop_long[df_pop_long["year"].between(2020, 2024)].copy()

    # Merge Abbr to get 2-letter codes
    df_pop_long = df_pop_long.rename(columns={"state": "state_name"})

    # Finds columns dynamically in abbreviation file
    name_col = [c for c in df_abbr_raw.columns if "name" in c.lower()][0]
    abbr_col = [c for c in df_abbr_raw.columns if "abbr" in c.lower()][0]
    df_abbr = df_abbr_raw.rename(columns={name_col: "state_name", abbr_col: "state"})

    df_abbr["state_name_key"] = df_abbr["state_name"].str.strip().str.lower()
    df_pop_long["state_name_key"] = df_pop_long["state_name"].str.strip().str.lower()

    df_pop_final = df_pop_long.merge(
        df_abbr[["state_name_key", "state"]], on="state_name_key", how="left"
    ).dropna(subset=["state", "population"])

    return df_grants, df_trump, df_pop_final, df_abbr


# Load Data
df_grants, df_trump, df_pop, df_abbr = load_data()

if df_grants is None:
    st.stop()


# -----------------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to Question:",
    [
        "🏠 Home / Overview",
        "Q1: Grants by State",
        "Q2: Grants by Directorate",
        "Q3: Cancellations Analysis",
        "Q4: Funding Evolution",
        "Q5: State Impact Profile",
        "Q6: Population Efficiency",
        "📊 Dashboard View",
    ],
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Project 2**\n\n"
    "Exploratory Visualization Analysis of NSF Grants (2020-2024) "
    "and Trump-Era Cancellations."
)


# -----------------------------------------------------------------------------
# 4. PAGE LOGIC
# -----------------------------------------------------------------------------

# === HOME ===
if page == "🏠 Home / Overview":
    st.title("NSF Grants Analysis Dashboard")
    st.markdown(
        """
    Welcome to the **Exploratory Visualization Project** — an interactive analysis platform for exploring 
    National Science Foundation (NSF) grants data and funding patterns across the United States.
    """
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Dataset Overview")
        st.markdown(
            """
            **Active Grants Dataset:**
            - **Time Period:** 2020 - 2024 (Last 5 Years)
            - **Coverage:** All NSF-funded grants across all states and directorates
            - **Metrics:** Award amounts, grant counts, geographic distribution
            
            **Cancelled Grants Dataset:**
            - **Time Period:** 2017 - 2021 (Trump Administration Era)
            - **Coverage:** Grants that were explicitly terminated during this period
            - **Purpose:** Comparative analysis of funding disruptions
            """
        )

    with col2:
        st.subheader("🎯 Research Questions")
        st.markdown(
            """
            This dashboard addresses **6 key research questions:**
            
            1. **Q1:** How are grants distributed by state?
            2. **Q2:** How are grants distributed per directorate?
            3. **Q3:** Are cancelled grants hitting certain directorates?
            4. **Q4:** How have total grants evolved over the years?
            5. **Q5:** How have grants evolved for selected states?
            6. **Q6:** What is the funding efficiency per capita?
            """
        )

    st.markdown("---")

    st.subheader("📋 Data Sources")

    st.markdown(
        """
        - **NSF Award Search Portal:** Official source for all grant data
        - **Population Data:** Estimated state populations (2020-2024)
        - **State Abbreviations:** Standardized state name mappings
        
        All data has been cleaned and processed for optimal visualization performance.
        """
    )

# === Q1: STATE DISTRIBUTION ===
elif page == "Q1: Grants by State":
    st.header("Q1: How are grants distributed by state?")
    st.markdown(
        "Analyze the geographic distribution of funding. Toggle between specific years or view the aggregate total."
    )

    # Data Prep
    q1_yearly = (
        df_grants.groupby(["state", "year"])
        .agg(grants_count=("award_id", "count"), total_amount=("award_amount", "sum"))
        .reset_index()
    )
    q1_total = (
        df_grants.groupby(["state"])
        .agg(grants_count=("award_id", "count"), total_amount=("award_amount", "sum"))
        .reset_index()
    )
    q1_total["year"] = 0
    q1_full = pd.concat([q1_yearly, q1_total], ignore_index=True)

    # Inputs
    years = sorted(q1_yearly["year"].unique())
    year_options = [0] + years
    year_labels = ["All Years (Total)"] + [str(y) for y in years]

    # Altair Selectors
    input_dropdown = alt.binding_select(
        options=year_options, labels=year_labels, name="Select Year: "
    )
    year_select = alt.selection_point(
        fields=["year"], bind=input_dropdown, value=[{"year": 0}]
    )
    state_select = alt.selection_point(fields=["state"], empty="all")

    # Chart
    bars = (
        alt.Chart(q1_full)
        .mark_bar()
        .encode(
            x=alt.X("state:N", sort="-y", title="State"),
            y=alt.Y("grants_count:Q", title="Number of Grants"),
            color=alt.condition(
                state_select,
                alt.Color(
                    "grants_count:Q", scale=alt.Scale(scheme="blues"), legend=None
                ),
                alt.value("#f0f0f0"),
            ),
            tooltip=[
                "state",
                "year",
                "grants_count",
                alt.Tooltip("total_amount", format="$,.0f"),
            ],
        )
        .add_params(year_select, state_select)
        .transform_filter(year_select)
        .properties(width=600, height=450, title="Grants by State")
    )

    trend = (
        alt.Chart(q1_yearly)
        .mark_line(point=True)
        .encode(
            x="year:O",
            y=alt.Y("total_amount:Q", axis=alt.Axis(format="~s"), title="Funding ($)"),
            color=alt.value("#4c78a8"),
            tooltip=["year", alt.Tooltip("total_amount", format="$,.0f")],
        )
        .transform_filter(state_select)
        .properties(width=300, height=200, title="History (Selected State)")
    )

    kpi = (
        alt.Chart(q1_full)
        .transform_filter(year_select)
        .transform_filter(state_select)
        .mark_text(color="#333", fontSize=20, fontWeight="bold")
        .encode(text=alt.Text("sum(total_amount):Q", format="$,.0f"))
        .properties(width=300, height=50, title="Total Funding (Selection)")
    )

    # Layout
    st.altair_chart(
        (bars | (trend & kpi)).resolve_scale(color="independent"),
        use_container_width=True,
    )

    with st.expander("See Design Justification"):
        st.markdown(
            """
            **Design Rationale:**
            
            To analyze grant distribution by state, I implemented a **composite dashboard** centered on a sorted bar chart. 
            A bar chart was chosen over a choropleth map for the primary view because it allows for precise ranking and 
            direct comparison of grant magnitudes, which are often obscured by geography in map views.
            
            The design follows Shneiderman's mantra: the bars provide the **overview** for the selected year. The **filtering** 
            mechanism (year dropdown) enables temporal exploration, allowing users to observe shifts in distribution over time. 
            **Details-on-demand** are achieved through linking: clicking a specific state isolates it visually (using a 
            "focus+context" gray/blue color scheme) and triggers the side panels showing historical trends and total funding.
            """
        )


# === Q2: DIRECTORATE DISTRIBUTION ===
elif page == "Q2: Grants by Directorate":
    st.header("Q2: How are grants distributed per directorate?")
    st.markdown(
        "Compare funding across different NSF directorates. Click a bar to see its funding history."
    )

    # Data Prep
    q2_yearly = (
        df_grants.groupby(["directorate", "year"])
        .agg(grants_count=("award_id", "count"), total_amount=("award_amount", "sum"))
        .reset_index()
    )
    q2_total = (
        df_grants.groupby(["directorate"])
        .agg(grants_count=("award_id", "count"), total_amount=("award_amount", "sum"))
        .reset_index()
    )
    q2_total["year"] = 0
    q2_full = pd.concat([q2_yearly, q2_total], ignore_index=True)

    years = sorted(q2_yearly["year"].unique())
    year_options = [0] + years
    year_labels = ["All Years (Total)"] + [str(y) for y in years]

    input_dropdown = alt.binding_select(
        options=year_options, labels=year_labels, name="Select Year: "
    )
    year_select = alt.selection_point(
        fields=["year"], bind=input_dropdown, value=[{"year": 0}]
    )
    dir_select = alt.selection_point(fields=["directorate"], empty="all")

    bars = (
        alt.Chart(q2_full)
        .mark_bar()
        .encode(
            x=alt.X("grants_count:Q", title="Number of Grants"),
            y=alt.Y("directorate:N", sort="-x", title="Directorate"),
            color=alt.condition(
                dir_select,
                alt.Color(
                    "grants_count:Q", scale=alt.Scale(scheme="blues"), legend=None
                ),
                alt.value("#f0f0f0"),
            ),
            tooltip=[
                "directorate",
                "year",
                "grants_count",
                alt.Tooltip("total_amount", format="$,.0f"),
            ],
        )
        .add_params(year_select, dir_select)
        .transform_filter(year_select)
        .properties(width=500, height=500, title="Grants by Directorate")
    )

    trend = (
        alt.Chart(q2_yearly)
        .mark_line(point=True)
        .encode(
            x="year:O",
            y=alt.Y("total_amount:Q", axis=alt.Axis(format="~s"), title="Funding ($)"),
            color=alt.value("#4c78a8"),
            tooltip=["year", alt.Tooltip("total_amount", format="$,.0f")],
        )
        .transform_filter(dir_select)
        .properties(width=350, height=250, title="History (Selected Directorate)")
    )

    kpi = (
        alt.Chart(q2_full)
        .transform_filter(year_select)
        .transform_filter(dir_select)
        .mark_text(color="#333", fontSize=20, fontWeight="bold")
        .encode(text=alt.Text("sum(total_amount):Q", format="$,.0f"))
        .properties(width=350, height=50, title="Total Funding (Selection)")
    )

    st.altair_chart(
        (bars | (trend & kpi)).resolve_scale(color="independent"),
        use_container_width=True,
    )

    with st.expander("See Design Justification"):
        st.markdown(
            """
            **Design Rationale:**
            
            To analyze grant distribution across the 47+ NSF directorates, I designed a **composite dashboard** centered on 
            a sorted horizontal bar chart. This provides a clear 'Leaderboard' of funding volume, which is essential for 
            comparing such a large number of categories.
            
            Adhering to the **Details-on-Demand** principle, clicking a directorate reveals its specific historical context 
            in the side panel: a **Trend Line** showing funding evolution over the last 5 years and a **KPI Text** displaying 
            the exact dollar amount for the selected timeframe. This separation ensures the main view remains an uncluttered 
            overview while providing deep-dive data when needed.
            """
        )


# === Q3: CANCELLATIONS ===
elif page == "Q3: Cancellations Analysis":
    st.header("Q3: Are cancelled grants hitting a certain directorate?")
    st.markdown(
        "Identify disproportionate targeting by comparing Directorate Size (X) vs. Cancellations (Y)."
    )

    # Data Prep
    base = (
        df_grants.groupby(["directorate"])
        .agg(base_count=("award_id", "count"))
        .reset_index()
    )
    cancel = (
        df_trump.groupby(["directorate"])
        .agg(cancel_count=("award_id", "count"), lost_amt=("award_amount", "sum"))
        .reset_index()
    )
    q3_df = base.merge(cancel, on="directorate", how="outer").fillna(0)
    q3_df["rate"] = q3_df["cancel_count"] / q3_df["base_count"].replace(0, 1)

    dir_select = alt.selection_point(fields=["directorate"], empty="all")

    scatter = (
        alt.Chart(q3_df)
        .mark_circle(stroke="black", strokeWidth=1)
        .encode(
            x=alt.X("base_count:Q", title="Directorate Size (Total Grants)"),
            y=alt.Y("cancel_count:Q", title="Cancellations"),
            size=alt.Size(
                "lost_amt:Q", title="Lost Funding", scale=alt.Scale(range=[100, 1000])
            ),
            color=alt.condition(
                dir_select, alt.value("#d62728"), alt.value("lightgray")
            ),
            tooltip=[
                "directorate",
                "base_count",
                "cancel_count",
                alt.Tooltip("lost_amt", format="$,.0f"),
            ],
        )
        .add_params(dir_select)
        .interactive()
        .properties(width=500, height=400, title="Volume vs. Cancellations")
    )

    bars = (
        alt.Chart(q3_df)
        .mark_bar()
        .encode(
            x=alt.X("cancel_count:Q", title="Cancellations"),
            y=alt.Y("directorate:N", sort="-x", title="Directorate"),
            color=alt.condition(
                dir_select,
                alt.Color(
                    "cancel_count:Q", scale=alt.Scale(scheme="reds"), legend=None
                ),
                alt.value("#f0f0f0"),
            ),
        )
        .add_params(dir_select)
        .properties(width=300, height=400, title="Ranking")
    )

    st.altair_chart(
        (bars | scatter).resolve_scale(color="independent"), use_container_width=True
    )

    with st.expander("See Design Justification"):
        st.markdown(
            """
            **Design Rationale:**
            
            To determine if cancellations disproportionately targeted specific directorates, I designed a **composite dashboard** 
            that distinguishes **volume** from **intensity**. A raw count is biased by directorate size, so I paired a **Ranked 
            Bar Chart** (Left) for absolute impact with an **Interactive Scatter Plot** (Right) for relative context.
            
            The Scatter Plot plots Directorate Size (X) vs. Cancellations (Y). This design effectively separates natural scaling 
            (diagonal trend) from anomalies (outliers high on Y but low on X), allowing users to pinpoint specific targets.
            
            Adhering to Shneiderman's mantra, the dashboard supports **Zoom & Pan** on the scatter plot to resolve occlusion 
            in dense clusters. **Insight:** Directorates high on the Y-axis but low on the X-axis (Outliers) were disproportionately 
            targeted relative to their size.
            """
        )


# === Q4: FUNDING EVOLUTION ===
elif page == "Q4: Funding Evolution":
    st.header("Q4: How have total grants evolved over the years?")

    # Data Prep
    q4_df = (
        df_grants.groupby(["year", "state", "directorate"])
        .agg(total_amount=("award_amount", "sum"), grants_count=("award_id", "count"))
        .reset_index()
    )

    # Streamlit Filters (Better than Altair binding for this volume)
    col1, col2 = st.columns(2)
    with col1:
        sel_state = st.selectbox(
            "Filter by State", ["All"] + sorted(q4_df["state"].unique())
        )
    with col2:
        sel_dir = st.selectbox(
            "Filter by Directorate", ["All"] + sorted(q4_df["directorate"].unique())
        )

    # Filter Data
    filtered_df = q4_df.copy()
    if sel_state != "All":
        filtered_df = filtered_df[filtered_df["state"] == sel_state]
    if sel_dir != "All":
        filtered_df = filtered_df[filtered_df["directorate"] == sel_dir]

    # Chart
    area = (
        alt.Chart(filtered_df)
        .mark_area(
            line={"color": "#4c78a8"},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="#4c78a8", offset=0),
                    alt.GradientStop(color="white", offset=1),
                ],
                x1=1,
                x2=1,
                y1=1,
                y2=0,
            ),
            opacity=0.6,
        )
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y(
                "sum(total_amount):Q",
                title="Total Funding ($)",
                axis=alt.Axis(format="~s"),
            ),
            tooltip=["year", alt.Tooltip("sum(total_amount)", format="$,.0f")],
        )
        .properties(height=400, title="Funding Evolution")
    )

    st.altair_chart(area, use_container_width=True)

    with st.expander("See Design Justification"):
        st.markdown(
            """
            **Design Rationale:**
            
            To visualize funding evolution over time, I designed an **Area Chart** that aggregates total funding by year. 
            This visualization allows users to observe overall trends and patterns in NSF grant funding across the 5-year period.
            
            The design supports **multi-dimensional filtering** through State and Directorate selectors, enabling users to 
            drill down from the aggregate view to specific geographic or organizational contexts. The area chart's gradient 
            fill provides visual weight to the temporal progression while maintaining clarity.
            """
        )


# === Q5: STATE PROFILE ===
elif page == "Q5: State Impact Profile":
    st.header("Q5: State Evolution & Cancellations")
    st.markdown(
        "A dual-view profile showing the funding health (top) vs. the cancellation impact (bottom)."
    )

    # Selector
    selected_state = st.selectbox(
        "Select State to Analyze:", sorted(df_grants["state"].unique()), index=4
    )  # Default CA

    # Data Prep (Master Timeline)
    grants_agg = (
        df_grants[df_grants["state"] == selected_state]
        .groupby("year")
        .agg(g_cnt=("award_id", "count"), g_amt=("award_amount", "sum"))
        .reset_index()
    )
    trump_agg = (
        df_trump[df_trump["state"] == selected_state]
        .groupby("year")
        .agg(c_cnt=("award_id", "count"), c_amt=("award_amount", "sum"))
        .reset_index()
    )

    years = range(2017, 2025)
    master = pd.DataFrame({"year": years})
    master = (
        master.merge(grants_agg, on="year", how="left")
        .merge(trump_agg, on="year", how="left")
        .fillna(0)
    )

    # Charts
    base = alt.Chart(master).encode(x=alt.X("year:O", title=None))

    top = (
        alt.layer(
            base.mark_bar(color="#9ecae1", opacity=0.7).encode(
                y=alt.Y("g_cnt:Q", title="Grants Count")
            ),
            base.mark_line(color="#08519c", strokeWidth=3).encode(
                y=alt.Y(
                    "g_amt:Q",
                    title="Funding ($)",
                    axis=alt.Axis(format="~s", titleColor="#08519c"),
                )
            ),
        )
        .resolve_scale(y="independent")
        .properties(height=250, title=f"Evolution: {selected_state} (Volume vs Value)")
    )

    bot = (
        alt.layer(
            base.mark_bar(color="#fc9272", opacity=0.7).encode(
                y=alt.Y("c_cnt:Q", title="Cancelled")
            ),
            base.mark_line(color="#de2d26", strokeWidth=3).encode(
                y=alt.Y(
                    "c_amt:Q",
                    title="Lost ($)",
                    axis=alt.Axis(format="~s", titleColor="#de2d26"),
                )
            ),
        )
        .resolve_scale(y="independent")
        .properties(height=150, title=f"Impact: {selected_state} Cancellations")
    )

    st.altair_chart(alt.vconcat(top, bot, spacing=5), use_container_width=True)

    with st.expander("See Design Justification"):
        st.markdown(
            """
            **Design Rationale:**
            
            To provide a comprehensive view of state-level funding evolution, I designed a **vertically stacked, dual-axis dashboard**. 
            This layout enables a direct 'cause-and-effect' comparison between the funding ecosystem (Top) and the cancellation 
            impact (Bottom) on a synchronized timeline.
            
            The top panel uses a **dual-axis design** combining bar charts (grant counts) with line charts (funding amounts) to 
            show both volume and value metrics simultaneously. The bottom panel similarly visualizes cancellation data, allowing 
            users to correlate funding patterns with cancellation impacts for any selected state.
            """
        )


# === Q6: EFFICIENCY ===
elif page == "Q6: Population Efficiency":
    st.header("Q6: Funding Per Capita Efficiency")
    st.markdown(
        "Investigate funding efficiency by comparing State Population (X) vs. Funding Per Capita (Y)."
    )

    # 1. LOAD & CLEAN
    df_pop_raw_q6 = pd.read_csv("estimated_population.csv")
    df_abbr_raw_q6 = pd.read_csv("state_abbreviations.csv")

    # Clean cols
    df_pop_raw_q6.columns = df_pop_raw_q6.columns.str.strip()
    df_abbr_raw_q6.columns = df_abbr_raw_q6.columns.str.strip()

    # Melt Population
    pop_cols = [c for c in df_pop_raw_q6.columns if c.lower().startswith("pop_")]
    df_pop_long = df_pop_raw_q6.melt(
        id_vars=["state"], value_vars=pop_cols, var_name="year", value_name="population"
    )
    df_pop_long["year"] = (
        df_pop_long["year"].str.replace("pop_", "", regex=False).astype(int)
    )
    df_pop_long["population"] = pd.to_numeric(df_pop_long["population"], errors="coerce")
    df_pop_long = df_pop_long[df_pop_long["year"].between(2020, 2024)].copy()
    df_pop_long = df_pop_long.rename(columns={"state": "state_name"})
    df_pop_long["state_name"] = df_pop_long["state_name"].astype(str).str.strip()

    # Clean Abbreviations
    df_abbr_q6 = df_abbr_raw_q6.copy()
    name_col = [
        c for c in df_abbr_q6.columns if "name" in c.lower() or (c.lower() == "state")
    ][0]
    abbr_col = [c for c in df_abbr_q6.columns if "abbr" in c.lower() or "code" in c.lower()][0]
    df_abbr_q6 = df_abbr_q6.rename(columns={name_col: "state_name", abbr_col: "state"})
    df_abbr_q6["state_name"] = df_abbr_q6["state_name"].astype(str).str.strip()
    df_abbr_q6["state"] = df_abbr_q6["state"].astype(str).str.strip()

    # Merge Pop + Abbr
    df_abbr_q6["state_name_key"] = df_abbr_q6["state_name"].str.lower()
    df_pop_long["state_name_key"] = df_pop_long["state_name"].str.lower()
    df_pop_long = df_pop_long.merge(
        df_abbr_q6[["state_name_key", "state"]], on="state_name_key", how="left"
    )
    df_pop_long = df_pop_long.dropna(subset=["state", "population"])
    df_pop_long = df_pop_long[["state", "year", "population"]].copy()

    # NSF Data Prep
    df_grants_q6 = df_grants.copy()
    df_grants_q6["year"] = pd.to_numeric(df_grants_q6["year"], errors="coerce").astype(int)

    # --- AGGREGATE "ALL YEARS" DATA (Year 0) ---
    # A. Yearly Data
    q6_yearly = (
        df_grants_q6.dropna(subset=["state", "year", "award_amount"])
        .groupby(["state", "year"])
        .agg(total_amount=("award_amount", "sum"), grants_count=("award_id", "count"))
        .reset_index()
    )

    # B. Global Data (Year 0)
    q6_total_grants = (
        df_grants_q6.dropna(subset=["state", "award_amount"])
        .groupby(["state"])
        .agg(total_amount=("award_amount", "sum"), grants_count=("award_id", "count"))
        .reset_index()
    )
    q6_total_grants["year"] = 0

    # 3. PREPARE POPULATION FOR YEAR 0
    pop_avg = df_pop_long.groupby("state")["population"].mean().reset_index()
    pop_avg["year"] = 0

    # Combine Pop Data (Yearly + Year 0)
    df_pop_full = pd.concat([df_pop_long, pop_avg], ignore_index=True)

    # Combine Grants Data (Yearly + Year 0)
    q6_grants_full = pd.concat([q6_yearly, q6_total_grants], ignore_index=True)

    # Merge All
    q6_df = q6_grants_full.merge(df_pop_full, on=["state", "year"], how="inner")
    q6_df["funding_per_capita"] = q6_df["total_amount"] / q6_df["population"]

    # CALCULATE NATIONAL AVERAGES
    us_avg = q6_df.groupby("year")["funding_per_capita"].mean().reset_index()
    us_avg = us_avg.rename(columns={"funding_per_capita": "us_avg_per_capita"})
    q6_df = q6_df.merge(us_avg, on="year", how="left")

    # 2. INTERACTION SETUP
    years = sorted(q6_df["year"].unique())
    year_options = years
    year_labels = ["All Years (Total)"] + [str(y) for y in years if y != 0]

    input_element = alt.binding_select(
        options=year_options, labels=year_labels, name="Select Year: "
    )

    year_select = alt.selection_point(
        name="year_select", fields=["year"], bind=input_element, value=[{"year": 0}]
    )
    state_select = alt.selection_point(
        name="state_select", fields=["state"], empty="all", on="click", clear="dblclick"
    )

    # 3. LEFT CHART: SCATTER PLOT
    base_scatter = alt.Chart(q6_df).transform_filter(year_select)

    points = (
        base_scatter.mark_circle(size=120, opacity=0.8, stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("population:Q", title="State Population", axis=alt.Axis(format="~s")),
            y=alt.Y(
                "funding_per_capita:Q",
                title="Funding Per Capita ($)",
                axis=alt.Axis(format="$,.0f"),
            ),
            color=alt.condition(
                state_select,
                alt.Color(
                    "funding_per_capita:Q", scale=alt.Scale(scheme="viridis"), legend=None
                ),
                alt.value("lightgray"),
            ),
            size=alt.condition(state_select, alt.value(150), alt.value(80)),
            tooltip=[
                alt.Tooltip("state:N", title="State"),
                alt.Tooltip("population:Q", format=",.0f"),
                alt.Tooltip("total_amount:Q", format="$,.0f", title="Total Funding"),
                alt.Tooltip("funding_per_capita:Q", format="$,.2f", title="Per Capita"),
            ],
        )
        .add_params(state_select, year_select)
        .interactive()
    )

    rule = base_scatter.mark_rule(color="red", strokeDash=[5, 5], size=2).encode(
        y="mean(us_avg_per_capita):Q",
        tooltip=[
            alt.Tooltip(
                "mean(us_avg_per_capita):Q", format="$,.2f", title="National Average"
            )
        ],
    )

    rule_text = base_scatter.mark_text(
        align="left", dx=5, dy=-5, color="red", fontWeight="bold"
    ).encode(
        y=alt.Y("mean(us_avg_per_capita):Q"), x=alt.value(0), text=alt.value("National Avg")
    )

    left_chart = (points + rule + rule_text).properties(
        width=500, height=400, title="Efficiency Matrix: Population vs. Funding Intensity"
    )

    # 4. RIGHT PANEL: DETAILS & HISTORY
    # A. Trend Comparison
    history_base = alt.Chart(q6_df[q6_df["year"] != 0]).transform_filter(state_select)

    state_line = history_base.mark_line(point=True, strokeWidth=4, color="#440154").encode(
        x=alt.X("year:O", title="Year"),
        y=alt.Y("funding_per_capita:Q", title="$/Person"),
        tooltip=["year", alt.Tooltip("funding_per_capita", format="$,.2f")],
    )

    avg_line = (
        alt.Chart(us_avg[us_avg["year"] != 0])
        .mark_line(strokeDash=[5, 5], color="red", opacity=0.5)
        .encode(x=alt.X("year:O"), y=alt.Y("us_avg_per_capita:Q"))
    )

    history_chart = (
        (avg_line + state_line)
        .transform_filter(state_select)
        .properties(
            width=350, height=200, title="History: Selected State vs. National Avg (Red)"
        )
    )

    # B. KPI Block
    kpi_base = alt.Chart(q6_df).transform_filter(year_select).transform_filter(state_select)

    def make_kpi(label, value_col, fmt, y_pos):
        lbl = kpi_base.mark_text(align="center", color="#666", fontSize=12).encode(
            text=alt.value(label), x=alt.value(175), y=alt.value(y_pos)
        )
        val = kpi_base.mark_text(
            align="center", color="#333", fontSize=20, fontWeight="bold"
        ).encode(
            text=alt.Text(value_col, format=fmt), x=alt.value(175), y=alt.value(y_pos + 20)
        )
        return lbl + val

    kpis = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rect(opacity=0)
        .properties(width=350, height=180)
        + make_kpi("State Population", "mean(population):Q", ",.0f", 20)
        + make_kpi("Total Funding Received", "sum(total_amount):Q", "$,.2s", 80)
        + make_kpi("Per Capita Funding", "mean(funding_per_capita):Q", "$,.2f", 140)
    )

    # 5. ASSEMBLE
    right_panel = alt.vconcat(history_chart, kpis, spacing=20)

    final_q6 = (
        (left_chart | right_panel).configure_view(stroke=None).configure_concat(spacing=20)
    )

    st.altair_chart(final_q6, use_container_width=True)

    with st.expander("See Design Justification"):
        st.markdown(
            """
            **Design Rationale:**
            
            For the final analysis, I designed an **'Efficiency Matrix' Scatter Plot** to normalize funding against state size. 
            By plotting **Population (X)** versus **Funding Per Capita (Y)**, this visualization instantly reveals structural 
            disparities that raw totals hide—specifically, identifying small states with high research intensity (top-left) 
            versus large states that are relatively underfunded (bottom-right).
            
            The log scale on the X-axis accommodates the wide range of state populations while maintaining readability. 
            The **National Average line** (red dashed) provides a benchmark for comparison, allowing users to quickly identify 
            states that outperform or underperform relative to the national mean.
            
            **How to read this chart:**
            - **Top Left:** Small states with high funding intensity (Specialists/EPSCoR).
            - **Bottom Right:** Large states with lower funding per person.
            - **Red Line:** The National Average for that year. States above are 'beating' the average.
            """
        )


# === DASHBOARD VIEW ===
elif page == "📊 Dashboard View":
    st.header("📊 Complete Dashboard View")
    st.markdown("Overview of all 6 research questions in a single screen.")

    # Prepare all data for dashboard
    all_years = sorted([y for y in df_grants["year"].unique() if y != 0])
    all_states = sorted(df_grants["state"].unique())
    all_dirs = sorted(df_grants["directorate"].unique())

    # --- Q1 PREP ---
    q1_yearly = (
        df_grants.groupby(["state", "year"])
        .agg(grants_count=("award_id", "count"), total_amount=("award_amount", "sum"))
        .reset_index()
    )
    q1_total = (
        df_grants.groupby(["state"])
        .agg(grants_count=("award_id", "count"), total_amount=("award_amount", "sum"))
        .reset_index()
    )
    q1_total["year"] = 0
    q1_full = pd.concat([q1_yearly, q1_total], ignore_index=True)

    # --- Q2 PREP ---
    q2_yearly = (
        df_grants.groupby(["directorate", "year"])
        .agg(grants_count=("award_id", "count"), total_amount=("award_amount", "sum"))
        .reset_index()
    )
    q2_total = (
        df_grants.groupby(["directorate"])
        .agg(grants_count=("award_id", "count"), total_amount=("award_amount", "sum"))
        .reset_index()
    )
    q2_total["year"] = 0
    q2_full = pd.concat([q2_yearly, q2_total], ignore_index=True)

    # --- Q3 PREP (matches individual page) ---
    base = (
        df_grants.groupby(["directorate"])
        .agg(base_count=("award_id", "count"))
        .reset_index()
    )
    cancel = (
        df_trump.groupby(["directorate"])
        .agg(cancel_count=("award_id", "count"), lost_amt=("award_amount", "sum"))
        .reset_index()
    )
    q3_df = base.merge(cancel, on="directorate", how="outer").fillna(0)
    q3_df["rate"] = q3_df["cancel_count"] / q3_df["base_count"].replace(0, 1)

    # --- Q4 PREP ---
    q4_df = (
        df_grants.groupby(["year", "state", "directorate"])
        .agg(total_amount=("award_amount", "sum"), grants_count=("award_id", "count"))
        .reset_index()
    )

    # --- Q5 PREP ---
    q5_data = pd.DataFrame(
        list(itertools.product(all_states, range(2017, 2025))),
        columns=["state", "year"],
    )
    q5_data = q5_data.merge(
        df_grants.groupby(["state", "year"])["award_amount"]
        .sum()
        .rename("fund")
        .reset_index(),
        on=["state", "year"],
        how="left",
    )
    q5_data = q5_data.merge(
        df_trump.groupby(["state", "year"])["award_amount"]
        .sum()
        .rename("lost")
        .reset_index(),
        on=["state", "year"],
        how="left",
    ).fillna(0)

    # --- Q6 PREP (matches individual page) ---
    df_pop_raw_q6 = pd.read_csv("estimated_population.csv")
    df_abbr_raw_q6 = pd.read_csv("state_abbreviations.csv")

    # Clean cols
    df_pop_raw_q6.columns = df_pop_raw_q6.columns.str.strip()
    df_abbr_raw_q6.columns = df_abbr_raw_q6.columns.str.strip()

    # Melt Population
    pop_cols = [c for c in df_pop_raw_q6.columns if c.lower().startswith("pop_")]
    df_pop_long = df_pop_raw_q6.melt(
        id_vars=["state"], value_vars=pop_cols, var_name="year", value_name="population"
    )
    df_pop_long["year"] = (
        df_pop_long["year"].str.replace("pop_", "", regex=False).astype(int)
    )
    df_pop_long["population"] = pd.to_numeric(df_pop_long["population"], errors="coerce")
    df_pop_long = df_pop_long[df_pop_long["year"].between(2020, 2024)].copy()
    df_pop_long = df_pop_long.rename(columns={"state": "state_name"})
    df_pop_long["state_name"] = df_pop_long["state_name"].astype(str).str.strip()

    # Clean Abbreviations
    df_abbr_q6 = df_abbr_raw_q6.copy()
    name_col = [
        c for c in df_abbr_q6.columns if "name" in c.lower() or (c.lower() == "state")
    ][0]
    abbr_col = [c for c in df_abbr_q6.columns if "abbr" in c.lower() or "code" in c.lower()][0]
    df_abbr_q6 = df_abbr_q6.rename(columns={name_col: "state_name", abbr_col: "state"})
    df_abbr_q6["state_name"] = df_abbr_q6["state_name"].astype(str).str.strip()
    df_abbr_q6["state"] = df_abbr_q6["state"].astype(str).str.strip()

    # Merge Pop + Abbr
    df_abbr_q6["state_name_key"] = df_abbr_q6["state_name"].str.lower()
    df_pop_long["state_name_key"] = df_pop_long["state_name"].str.lower()
    df_pop_long = df_pop_long.merge(
        df_abbr_q6[["state_name_key", "state"]], on="state_name_key", how="left"
    )
    df_pop_long = df_pop_long.dropna(subset=["state", "population"])
    df_pop_long = df_pop_long[["state", "year", "population"]].copy()

    # NSF Data Prep
    df_grants_q6 = df_grants.copy()
    df_grants_q6["year"] = pd.to_numeric(df_grants_q6["year"], errors="coerce").astype(int)

    # AGGREGATE "ALL YEARS" DATA (Year 0)
    q6_yearly = (
        df_grants_q6.dropna(subset=["state", "year", "award_amount"])
        .groupby(["state", "year"])
        .agg(total_amount=("award_amount", "sum"), grants_count=("award_id", "count"))
        .reset_index()
    )

    q6_total_grants = (
        df_grants_q6.dropna(subset=["state", "award_amount"])
        .groupby(["state"])
        .agg(total_amount=("award_amount", "sum"), grants_count=("award_id", "count"))
        .reset_index()
    )
    q6_total_grants["year"] = 0

    # PREPARE POPULATION FOR YEAR 0
    pop_avg = df_pop_long.groupby("state")["population"].mean().reset_index()
    pop_avg["year"] = 0

    # Combine Pop Data (Yearly + Year 0)
    df_pop_full = pd.concat([df_pop_long, pop_avg], ignore_index=True)

    # Combine Grants Data (Yearly + Year 0)
    q6_grants_full = pd.concat([q6_yearly, q6_total_grants], ignore_index=True)

    # Merge All
    q6_df = q6_grants_full.merge(df_pop_full, on=["state", "year"], how="inner")
    q6_df["funding_per_capita"] = q6_df["total_amount"] / q6_df["population"]

    # CALCULATE NATIONAL AVERAGES
    us_avg = q6_df.groupby("year")["funding_per_capita"].mean().reset_index()
    us_avg = us_avg.rename(columns={"funding_per_capita": "us_avg_per_capita"})
    q6_df = q6_df.merge(us_avg, on="year", how="left")

    # ============================================================
    # ALTAIR INTERACTIVE CHARTS (FULL VERSION - MATCHES INDIVIDUAL PAGES)
    # ============================================================

    # --- Q1 CHART (matches individual page) ---
    years = sorted(q1_yearly["year"].unique())
    year_options = [0] + years
    year_labels = ["All Years (Total)"] + [str(y) for y in years]

    input_dropdown = alt.binding_select(
        options=year_options, labels=year_labels, name="Select Year: "
    )
    q1_yr_sel = alt.selection_point(
        fields=["year"], bind=input_dropdown, value=[{"year": 0}]
    )
    q1_st_sel = alt.selection_point(fields=["state"], empty="all")

    q1_bars = (
        alt.Chart(q1_full)
        .mark_bar()
        .encode(
            x=alt.X("state:N", sort="-y", title="State"),
            y=alt.Y("grants_count:Q", title="Number of Grants"),
            color=alt.condition(
                q1_st_sel,
                alt.Color(
                    "grants_count:Q", scale=alt.Scale(scheme="blues"), legend=None
                ),
                alt.value("#f0f0f0"),
            ),
            tooltip=[
                "state",
                "year",
                "grants_count",
                alt.Tooltip("total_amount", format="$,.0f"),
            ],
        )
        .add_params(q1_yr_sel, q1_st_sel)
        .transform_filter(q1_yr_sel)
        .properties(width=600, height=450, title="Q1: Grants by State")
    )

    q1_trend = (
        alt.Chart(q1_yearly)
        .mark_line(point=True)
        .encode(
            x="year:O",
            y=alt.Y("total_amount:Q", axis=alt.Axis(format="~s"), title="Funding ($)"),
            color=alt.value("#4c78a8"),
            tooltip=["year", alt.Tooltip("total_amount", format="$,.0f")],
        )
        .transform_filter(q1_st_sel)
        .properties(width=300, height=200, title="History (Selected State)")
    )

    q1_kpi = (
        alt.Chart(q1_full)
        .transform_filter(q1_yr_sel)
        .transform_filter(q1_st_sel)
        .mark_text(color="#333", fontSize=20, fontWeight="bold")
        .encode(text=alt.Text("sum(total_amount):Q", format="$,.0f"))
        .properties(width=300, height=50, title="Total Funding (Selection)")
    )

    q1_final = (q1_bars | (q1_trend & q1_kpi)).resolve_scale(color="independent")

    # --- Q2 CHART (matches individual page) ---
    years = sorted(q2_yearly["year"].unique())
    year_options = [0] + years
    year_labels = ["All Years (Total)"] + [str(y) for y in years]

    input_dropdown = alt.binding_select(
        options=year_options, labels=year_labels, name="Select Year: "
    )
    q2_yr_sel = alt.selection_point(
        fields=["year"], bind=input_dropdown, value=[{"year": 0}]
    )
    q2_dir_sel = alt.selection_point(fields=["directorate"], empty="all")

    q2_bars = (
        alt.Chart(q2_full)
        .mark_bar()
        .encode(
            x=alt.X("grants_count:Q", title="Number of Grants"),
            y=alt.Y("directorate:N", sort="-x", title="Directorate"),
            color=alt.condition(
                q2_dir_sel,
                alt.Color(
                    "grants_count:Q", scale=alt.Scale(scheme="blues"), legend=None
                ),
                alt.value("#f0f0f0"),
            ),
            tooltip=[
                "directorate",
                "year",
                "grants_count",
                alt.Tooltip("total_amount", format="$,.0f"),
            ],
        )
        .add_params(q2_yr_sel, q2_dir_sel)
        .transform_filter(q2_yr_sel)
        .properties(width=500, height=500, title="Q2: Grants by Directorate")
    )

    q2_trend = (
        alt.Chart(q2_yearly)
        .mark_line(point=True)
        .encode(
            x="year:O",
            y=alt.Y("total_amount:Q", axis=alt.Axis(format="~s"), title="Funding ($)"),
            color=alt.value("#4c78a8"),
            tooltip=["year", alt.Tooltip("total_amount", format="$,.0f")],
        )
        .transform_filter(q2_dir_sel)
        .properties(width=350, height=250, title="History (Selected Directorate)")
    )

    q2_kpi = (
        alt.Chart(q2_full)
        .transform_filter(q2_yr_sel)
        .transform_filter(q2_dir_sel)
        .mark_text(color="#333", fontSize=20, fontWeight="bold")
        .encode(text=alt.Text("sum(total_amount):Q", format="$,.0f"))
        .properties(width=350, height=50, title="Total Funding (Selection)")
    )

    q2_final = (q2_bars | (q2_trend & q2_kpi)).resolve_scale(color="independent")

    # --- Q3 CHART (matches individual page) ---
    q3_dir_sel = alt.selection_point(fields=["directorate"], empty="all")

    q3_scatter = (
        alt.Chart(q3_df)
        .mark_circle(stroke="black", strokeWidth=1)
        .encode(
            x=alt.X("base_count:Q", title="Directorate Size (Total Grants)"),
            y=alt.Y("cancel_count:Q", title="Cancellations"),
            size=alt.Size(
                "lost_amt:Q", title="Lost Funding", scale=alt.Scale(range=[100, 1000])
            ),
            color=alt.condition(
                q3_dir_sel, alt.value("#d62728"), alt.value("lightgray")
            ),
            tooltip=[
                "directorate",
                "base_count",
                "cancel_count",
                alt.Tooltip("lost_amt", format="$,.0f"),
            ],
        )
        .add_params(q3_dir_sel)
        .interactive()
        .properties(width=500, height=400, title="Q3: Volume vs. Cancellations")
    )

    q3_bars = (
        alt.Chart(q3_df)
        .mark_bar()
        .encode(
            x=alt.X("cancel_count:Q", title="Cancellations"),
            y=alt.Y("directorate:N", sort="-x", title="Directorate"),
            color=alt.condition(
                q3_dir_sel,
                alt.Color(
                    "cancel_count:Q", scale=alt.Scale(scheme="reds"), legend=None
                ),
                alt.value("#f0f0f0"),
            ),
        )
        .add_params(q3_dir_sel)
        .properties(width=300, height=400, title="Ranking")
    )

    q3_final = (q3_bars | q3_scatter).resolve_scale(color="independent")

    # --- Q4 CHART (matches individual page exactly) ---
    col_q4_1, col_q4_2 = st.columns(2)
    with col_q4_1:
        sel_state_q4 = st.selectbox(
            "Filter by State", ["All"] + sorted(q4_df["state"].unique()), key="q4_state"
        )
    with col_q4_2:
        sel_dir_q4 = st.selectbox(
            "Filter by Directorate", ["All"] + sorted(q4_df["directorate"].unique()), key="q4_dir"
        )

    # Filter Data
    filtered_df_q4 = q4_df.copy()
    if sel_state_q4 != "All":
        filtered_df_q4 = filtered_df_q4[filtered_df_q4["state"] == sel_state_q4]
    if sel_dir_q4 != "All":
        filtered_df_q4 = filtered_df_q4[filtered_df_q4["directorate"] == sel_dir_q4]

    q4_area = (
        alt.Chart(filtered_df_q4)
        .mark_area(
            line={"color": "#4c78a8"},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="#4c78a8", offset=0),
                    alt.GradientStop(color="white", offset=1),
                ],
                x1=1,
                x2=1,
                y1=1,
                y2=0,
            ),
            opacity=0.6,
        )
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y(
                "sum(total_amount):Q",
                title="Total Funding ($)",
                axis=alt.Axis(format="~s"),
            ),
            tooltip=["year", alt.Tooltip("sum(total_amount)", format="$,.0f")],
        )
        .properties(height=400, title="Q4: Funding Evolution")
    )

    q4_final = q4_area

    # --- Q5 CHART (matches individual page exactly) ---
    q5_selected_state = st.selectbox(
        "Select State to Analyze:", sorted(df_grants["state"].unique()), index=4, key="q5_state"
    )  # Default CA

    # Data Prep (Master Timeline) - matches individual page
    q5_grants_agg = (
        df_grants[df_grants["state"] == q5_selected_state]
        .groupby("year")
        .agg(g_cnt=("award_id", "count"), g_amt=("award_amount", "sum"))
        .reset_index()
    )
    q5_trump_agg = (
        df_trump[df_trump["state"] == q5_selected_state]
        .groupby("year")
        .agg(c_cnt=("award_id", "count"), c_amt=("award_amount", "sum"))
        .reset_index()
    )

    q5_years = range(2017, 2025)
    q5_master = pd.DataFrame({"year": q5_years})
    q5_master = (
        q5_master.merge(q5_grants_agg, on="year", how="left")
        .merge(q5_trump_agg, on="year", how="left")
        .fillna(0)
    )

    # Charts
    q5_base = alt.Chart(q5_master).encode(x=alt.X("year:O", title=None))

    q5_top = (
        alt.layer(
            q5_base.mark_bar(color="#9ecae1", opacity=0.7).encode(
                y=alt.Y("g_cnt:Q", title="Grants Count")
            ),
            q5_base.mark_line(color="#08519c", strokeWidth=3).encode(
                y=alt.Y(
                    "g_amt:Q",
                    title="Funding ($)",
                    axis=alt.Axis(format="~s", titleColor="#08519c"),
                )
            ),
        )
        .resolve_scale(y="independent")
        .properties(height=250, title=f"Q5: Evolution: {q5_selected_state} (Volume vs Value)")
    )

    q5_bot = (
        alt.layer(
            q5_base.mark_bar(color="#fc9272", opacity=0.7).encode(
                y=alt.Y("c_cnt:Q", title="Cancelled")
            ),
            q5_base.mark_line(color="#de2d26", strokeWidth=3).encode(
                y=alt.Y(
                    "c_amt:Q",
                    title="Lost ($)",
                    axis=alt.Axis(format="~s", titleColor="#de2d26"),
                )
            ),
        )
        .resolve_scale(y="independent")
        .properties(height=150, title=f"Impact: {q5_selected_state} Cancellations")
    )

    q5_final = alt.vconcat(q5_top, q5_bot, spacing=5)

    # --- Q6 CHART (matches individual page) ---
    years = sorted(q6_df["year"].unique())
    year_options = years
    year_labels = ["All Years (Total)"] + [str(y) for y in years if y != 0]

    input_element = alt.binding_select(
        options=year_options, labels=year_labels, name="Select Year: "
    )

    q6_yr_sel = alt.selection_point(
        name="year_select", fields=["year"], bind=input_element, value=[{"year": 0}]
    )
    q6_st_sel = alt.selection_point(
        name="state_select", fields=["state"], empty="all", on="click", clear="dblclick"
    )

    # LEFT CHART: SCATTER PLOT
    q6_base_scatter = alt.Chart(q6_df).transform_filter(q6_yr_sel)

    q6_points = (
        q6_base_scatter.mark_circle(size=120, opacity=0.8, stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("population:Q", title="State Population", axis=alt.Axis(format="~s")),
            y=alt.Y(
                "funding_per_capita:Q",
                title="Funding Per Capita ($)",
                axis=alt.Axis(format="$,.0f"),
            ),
            color=alt.condition(
                q6_st_sel,
                alt.Color(
                    "funding_per_capita:Q", scale=alt.Scale(scheme="viridis"), legend=None
                ),
                alt.value("lightgray"),
            ),
            size=alt.condition(q6_st_sel, alt.value(150), alt.value(80)),
            tooltip=[
                alt.Tooltip("state:N", title="State"),
                alt.Tooltip("population:Q", format=",.0f"),
                alt.Tooltip("total_amount:Q", format="$,.0f", title="Total Funding"),
                alt.Tooltip("funding_per_capita:Q", format="$,.2f", title="Per Capita"),
            ],
        )
        .add_params(q6_st_sel, q6_yr_sel)
        .interactive()
    )

    q6_rule = q6_base_scatter.mark_rule(color="red", strokeDash=[5, 5], size=2).encode(
        y="mean(us_avg_per_capita):Q",
        tooltip=[
            alt.Tooltip(
                "mean(us_avg_per_capita):Q", format="$,.2f", title="National Average"
            )
        ],
    )

    q6_rule_text = q6_base_scatter.mark_text(
        align="left", dx=5, dy=-5, color="red", fontWeight="bold"
    ).encode(
        y=alt.Y("mean(us_avg_per_capita):Q"), x=alt.value(0), text=alt.value("National Avg")
    )

    q6_left_chart = (q6_points + q6_rule + q6_rule_text).properties(
        width=500, height=400, title="Q6: Efficiency Matrix: Population vs. Funding Intensity"
    )

    # RIGHT PANEL: DETAILS & HISTORY
    q6_history_base = alt.Chart(q6_df[q6_df["year"] != 0]).transform_filter(q6_st_sel)

    q6_state_line = q6_history_base.mark_line(point=True, strokeWidth=4, color="#440154").encode(
        x=alt.X("year:O", title="Year"),
        y=alt.Y("funding_per_capita:Q", title="$/Person"),
        tooltip=["year", alt.Tooltip("funding_per_capita", format="$,.2f")],
    )

    q6_avg_line = (
        alt.Chart(us_avg[us_avg["year"] != 0])
        .mark_line(strokeDash=[5, 5], color="red", opacity=0.5)
        .encode(x=alt.X("year:O"), y=alt.Y("us_avg_per_capita:Q"))
    )

    q6_history_chart = (
        (q6_avg_line + q6_state_line)
        .transform_filter(q6_st_sel)
        .properties(
            width=350, height=200, title="History: Selected State vs. National Avg (Red)"
        )
    )

    # KPI Block
    q6_kpi_base = alt.Chart(q6_df).transform_filter(q6_yr_sel).transform_filter(q6_st_sel)

    def make_kpi(label, value_col, fmt, y_pos):
        lbl = q6_kpi_base.mark_text(align="center", color="#666", fontSize=12).encode(
            text=alt.value(label), x=alt.value(175), y=alt.value(y_pos)
        )
        val = q6_kpi_base.mark_text(
            align="center", color="#333", fontSize=20, fontWeight="bold"
        ).encode(
            text=alt.Text(value_col, format=fmt), x=alt.value(175), y=alt.value(y_pos + 20)
        )
        return lbl + val

    q6_kpis = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rect(opacity=0)
        .properties(width=350, height=180)
        + make_kpi("State Population", "mean(population):Q", ",.0f", 20)
        + make_kpi("Total Funding Received", "sum(total_amount):Q", "$,.2s", 80)
        + make_kpi("Per Capita Funding", "mean(funding_per_capita):Q", "$,.2f", 140)
    )

    q6_right_panel = alt.vconcat(q6_history_chart, q6_kpis, spacing=20)

    q6_final = (
        (q6_left_chart | q6_right_panel).configure_view(stroke=None).configure_concat(spacing=20)
    )

    # ============================================================
    # DISPLAY CHARTS (FULL VERSIONS - SAME AS INDIVIDUAL PAGES)
    # ============================================================

    st.markdown("### 📊 Complete Dashboard - All Questions (Full Interactive Versions)")

    st.markdown("#### Q1: Grants by State")
    st.altair_chart(q1_final, use_container_width=True)

    st.markdown("---")

    st.markdown("#### Q2: Grants by Directorate")
    st.altair_chart(q2_final, use_container_width=True)

    st.markdown("---")

    st.markdown("#### Q3: Cancellations Analysis")
    st.altair_chart(q3_final, use_container_width=True)

    st.markdown("---")

    st.markdown("#### Q4: Funding Evolution")
    st.altair_chart(q4_final, use_container_width=True)

    st.markdown("---")

    st.markdown("#### Q5: State Impact Profile")
    st.altair_chart(q5_final, use_container_width=True)

    st.markdown("---")

    st.markdown("#### Q6: Population Efficiency")
    st.altair_chart(q6_final, use_container_width=True)

    st.markdown("---")
    st.info(
        "💡 **Note:** These are the same full interactive visualizations as the individual question pages. "
        "Use the dropdowns and click interactions to explore the data!"
    )
