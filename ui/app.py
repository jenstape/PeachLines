import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import matplotlib.pyplot as plt
import geopandas as gpd

from core.graph import build_graph
from core.scoring import score_plan
from core.mcmc import run_mcmc, make_seed_plan

st.set_page_config(page_title="PeachLines", page_icon="🍑", layout="wide")

st.title("🍑 PeachLines")
st.markdown("**Georgia's Congressional Districts, Redrawn**")
st.markdown(
    "Generate alternative congressional district maps for Georgia using MCMC ensemble sampling. "
    "Compare each plan against the enacted map on compactness, population equality, "
    "partisan fairness, and VRA compliance."
)
st.divider()

@st.cache_resource(show_spinner="Loading Georgia precinct data...")
def load_data():
    G, gdf = build_graph()
    return G, gdf

G, gdf = load_data()

def plan_from_column(G, col='CD'):
    return {node: int(G.nodes[node][col]) for node in G.nodes()}

def plot_plan(plan, gdf, title="District Map"):
    gdf = gdf.copy()
    gdf['district'] = [plan.get(i, -1) for i in range(len(gdf))]
    fig, ax = plt.subplots(figsize=(7, 7))
    gdf.plot(column='district', categorical=True, cmap='tab20',
             edgecolor='white', linewidth=0.1, ax=ax, legend=False)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
    ax.set_axis_off()
    plt.tight_layout()
    return fig

def render_scores(results, label="Plan"):
    st.markdown(f"**{label}**")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Max population deviation",
                  f"{results['population']['max_deviation_pct']}%",
                  help="Congressional districts should be near 0%. Lower is better.")
        st.metric("Mean Polsby-Popper (compactness)",
                  f"{results['compactness']['mean_polsby_popper']}",
                  help="1.0 = perfect circle. Higher is better.")
    with col2:
        st.metric("Cut edges",
                  f"{results['cut_edges']['cut_edges']} / {results['cut_edges']['total_edges']}",
                  help="Lower = simpler boundaries.")
        gap = results['partisan']['efficiency_gap_pct']
        st.metric("Efficiency gap",
                  f"{gap}% ({results['partisan']['interpretation']})",
                  help="Near 0% is most symmetric. >8% is often cited as meaningful.")
    opp = results['vra']['opportunity_districts']
    st.metric("Black opportunity districts (BVAP ≥ 35%)", f"{opp}",
              help="VRA compliance proxy. Georgia courts require at least 2.")
    if opp < 2:
        st.warning(f"⚠️ Only {opp} Black opportunity district(s). Georgia courts require at least 2.")

with st.sidebar:
    st.header("Generate a new plan")
    mcmc_steps = st.slider("MCMC steps", 100, 2000, 500, 100,
                           help="More steps = more exploration, but slower.")
    max_pop_dev = st.slider("Max population deviation (%)", 1.0, 10.0, 5.0, 0.5)
    use_seed = st.checkbox("Use fixed random seed (reproducible)", value=False)
    random_seed = st.number_input("Seed value", value=42, step=1) if use_seed else None
    run_button = st.button("🔄 Generate new plan", type="primary", use_container_width=True)
    st.divider()
    st.markdown("**About PeachLines**\n\nBuilt with Python · geopandas · networkx · libpysal\n\nData: [MGGG States](https://github.com/mggg-states/GA-shapefiles)")

col_enacted, col_generated = st.columns(2)

with col_enacted:
    st.subheader("Enacted map (baseline)")
    enacted_plan = plan_from_column(G)
    enacted_scores = score_plan(enacted_plan, G, gdf)
    fig_enacted = plot_plan(enacted_plan, gdf, title="Georgia — Enacted Districts (pre-2023)")
    st.pyplot(fig_enacted)
    plt.close()
    render_scores(enacted_scores, label="Enacted map scores")

with col_generated:
    st.subheader("Generated plan")
    if run_button:
        progress_bar = st.progress(0, text="Running MCMC...")
        def update_progress(step, accepted, total):
            pct = int(step / total * 100)
            progress_bar.progress(pct, text=f"Step {step}/{total} — {accepted} accepted")
        with st.spinner(""):
            plans, stats = run_mcmc(G, steps=mcmc_steps,
                                    save_every=max(1, mcmc_steps // 10),
                                    max_pop_deviation=max_pop_dev,
                                    seed=random_seed,
                                    progress_callback=update_progress)
        progress_bar.empty()
        if len(plans) > 1:
            generated_plan = plans[-1]
        else:
            generated_plan = plans[0]
            st.warning("No new plans accepted. Try increasing steps or population deviation.")
        st.session_state['generated_plan'] = generated_plan
        st.session_state['mcmc_stats'] = stats

    if 'generated_plan' in st.session_state:
        generated_plan = st.session_state['generated_plan']
        stats = st.session_state['mcmc_stats']
        fig_gen = plot_plan(generated_plan, gdf, title="PeachLines — Generated Plan")
        st.pyplot(fig_gen)
        plt.close()
        generated_scores = score_plan(generated_plan, G, gdf)
        render_scores(generated_scores, label="Generated plan scores")
        with st.expander("MCMC run details"):
            st.write(f"Steps attempted: **{stats['steps_attempted']}**")
            st.write(f"Steps accepted: **{stats['steps_accepted']}**")
            st.write(f"Acceptance rate: **{stats['acceptance_rate']}%**")
            st.write(f"Plans saved: **{stats['plans_saved']}**")
    else:
        st.info("👈 Click **Generate new plan** to run MCMC and see an alternative map here.")
