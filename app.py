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
    Welcome to the **Exploratory Visualization Project**.
    
    This application allows you to interactively explore National Science Foundation (NSF) grants data 
    from the last 5 years, along with a comparative analysis of grants cancelled during the Trump administration.
    
    ### Dataset Overview
    - **Active Grants:** 2020 - 2024
    - **Cancelled Grants:** 2017 - 2021 (Trump Era)
    
    ### How to use
    Use the **Sidebar** to navigate through the 6 specific research questions (Q1 - Q6). 
    Each page contains interactive visualizations allowing you to filter by **Year**, **State**, and **Directorate**.
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
            "> **Design:** A Ranked Bar Chart provides a clear leaderboard. The Dropdown allows switching between global context and specific years. The linked Trend Line reveals the historical evolution of the selected state."
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

    with st.expander("Analysis"):
        st.markdown(
            "**Insight:** Directorates high on the Y-axis but low on the X-axis (Outliers) were disproportionately targeted relative to their size."
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


# === Q6: EFFICIENCY ===
elif page == "Q6: Population Efficiency":
    st.header("Q6: Funding Per Capita Efficiency")
    st.markdown(
        "Investigate funding efficiency by comparing State Population (X) vs. Funding Per Capita (Y)."
    )

    # Data Prep
    q6_grants = (
        df_grants.groupby(["state", "year"])
        .agg(total=("award_amount", "sum"))
        .reset_index()
    )
    q6_df = q6_grants.merge(
        df_pop, left_on=["state", "year"], right_on=["state", "year"], how="inner"
    )
    q6_df["per_capita"] = q6_df["total"] / q6_df["population"]

    # National Avg
    us_avg = (
        q6_df.groupby("year")["per_capita"]
        .mean()
        .reset_index()
        .rename(columns={"per_capita": "nat_avg"})
    )
    q6_df = q6_df.merge(us_avg, on="year")

    # Inputs
    sel_year = st.slider(
        "Select Year",
        int(q6_df["year"].min()),
        int(q6_df["year"].max()),
        int(q6_df["year"].max()),
    )

    # Chart
    subset = q6_df[q6_df["year"] == sel_year]

    base = alt.Chart(subset)

    scatter = (
        base.mark_circle(size=100, stroke="white")
        .encode(
            x=alt.X(
                "population:Q",
                scale=alt.Scale(type="log"),
                title="Population (Log Scale)",
            ),
            y=alt.Y("per_capita:Q", title="Funding Per Capita ($)"),
            color=alt.Color(
                "per_capita:Q", scale=alt.Scale(scheme="viridis"), legend=None
            ),
            tooltip=["state", "population", alt.Tooltip("per_capita", format="$,.2f")],
        )
        .properties(height=500, title=f"Efficiency Matrix ({sel_year})")
    )

    rule = base.mark_rule(color="red", strokeDash=[5, 5]).encode(y="mean(nat_avg):Q")
    text = base.mark_text(align="left", color="red", dy=-5).encode(
        y="mean(nat_avg):Q", x=alt.value(0), text=alt.value("National Avg")
    )

    st.altair_chart(scatter + rule + text, use_container_width=True)

    with st.expander("How to read this chart"):
        st.markdown(
            """
        - **Top Left:** Small states with high funding intensity (Specialists/EPSCoR).
        - **Bottom Right:** Large states with lower funding per person.
        - **Red Line:** The National Average for that year. States above are 'beating' the average.
        """
        )
