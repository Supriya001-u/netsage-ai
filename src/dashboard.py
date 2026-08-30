"""
dashboard.py
-------------
Streamlit dashboard for NetSage AI.

Run with:
    streamlit run src/dashboard.py

Shows:
  - Overall metrics (total cases, diagnosed, accepted/edited/rejected, agreement rate)
  - Issue-type analysis (VLAN/DHCP/DNS/routing/ACL/NAT/wireless/gateway)
  - Severity breakdown
  - Responsible AI panel (accepted/edited/rejected + human correction rate)
  - Case detail view (symptom, topology, evidence, rule findings, AI diagnosis,
    human review)

The dashboard is read-only over data/ and outputs/ — it never calls an LLM
itself; it reads whatever main.py has already produced (or falls back to
running the rule checker + mock AI diagnoser live for cases not yet reviewed,
since MOCK_MODE has no cost or API key requirement).
"""
import csv
import os

import pandas as pd
import streamlit as st

from ai_diagnoser import MOCK_MODE, diagnose
from case_loader import dataset_summary, get_case_by_id, load_cases
from human_review import agreement_rate, load_reviews, review_counts
from rule_checker import run_all_checks
from utils import DATA_DIR

st.set_page_config(page_title="NetSage AI Dashboard", layout="wide")

CATEGORY_LABELS = {
    "vlan": "VLAN", "gateway": "Gateway", "dhcp": "DHCP", "dns": "DNS",
    "routing": "Routing", "acl": "ACL", "nat": "NAT", "wireless": "Wireless",
}


@st.cache_data
def _load_cases():
    return load_cases()


@st.cache_data
def _load_responsible_ai_log():
    path = os.path.join(DATA_DIR, "responsible_ai_log.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def render_overview(cases, reviews):
    st.header("Overall metrics")
    counts = review_counts(reviews)
    diagnosed = len(reviews)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total cases", len(cases))
    col2.metric("Cases diagnosed", diagnosed)
    col3.metric("Accepted", counts["ACCEPT"])
    col4.metric("Edited", counts["EDIT"])
    col5.metric("Rejected", counts["REJECT"])
    rate = agreement_rate(reviews)
    col6.metric("AI-human agreement", f"{rate}%" if rate is not None else "—")

    mode_label = "MOCK (no API key required)" if MOCK_MODE else "LIVE LLM (Anthropic API)"
    st.caption(f"AI diagnoser mode: **{mode_label}**")


def render_issue_analysis(cases):
    st.header("Issue analysis")
    summary = dataset_summary(cases)
    df = pd.DataFrame([
        {"Category": CATEGORY_LABELS.get(k, k.title()), "Cases": v}
        for k, v in summary["by_category"].items()
    ])
    col1, col2 = st.columns([2, 1])
    with col1:
        st.bar_chart(df.set_index("Category"))
    with col2:
        st.dataframe(df, hide_index=True, width='stretch')


def render_severity(cases):
    st.header("Severity breakdown")
    summary = dataset_summary(cases)
    df = pd.DataFrame([
        {"Severity": k, "Cases": v} for k, v in summary["by_severity"].items()
    ])
    order = ["Low", "Medium", "High", "Critical"]
    df["Severity"] = pd.Categorical(df["Severity"], categories=order, ordered=True)
    df = df.sort_values("Severity")
    st.bar_chart(df.set_index("Severity"))


def render_responsible_ai(reviews):
    st.header("Responsible AI")
    counts = review_counts(reviews)
    total = sum(counts.values())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("AI accepted", counts["ACCEPT"])
    col2.metric("AI edited", counts["EDIT"])
    col3.metric("AI rejected", counts["REJECT"])
    correction_rate = round(100 * (counts["EDIT"] + counts["REJECT"]) / total, 1) if total else None
    col4.metric("Human correction rate", f"{correction_rate}%" if correction_rate is not None else "—")

    st.subheader("Responsible AI log (documented AI mistakes and corrections)")
    log = _load_responsible_ai_log()
    st.dataframe(pd.DataFrame(log), hide_index=True, width='stretch')
    st.caption(
        "These are the cases where NetSage AI's initial diagnosis was "
        "incomplete or wrong and a human reviewer corrected it — the core "
        "evidence for why human review is mandatory, not optional."
    )


def render_case_detail(cases, reviews):
    st.header("Case detail")
    case_id = st.selectbox("Select a case", [c["case_id"] for c in cases])
    case = get_case_by_id(case_id, cases)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Symptom")
        st.write(case["symptom"])
        st.subheader("Topology note")
        st.write(case["topology_note"])
        st.subheader("Show command evidence")
        for cmd, output in case["show_outputs"].items():
            with st.expander(cmd):
                st.code(output)

    with col2:
        st.subheader("Rule checker findings")
        findings = run_all_checks(case)
        fired = [f for f in findings if f["status"] != "PASS"]
        if not fired:
            st.info("No deterministic rule fired — this case needs AI evidence reasoning.")
        for f in fired:
            icon = "🔴" if f["status"] == "FAIL" else "🟡"
            st.markdown(f"{icon} **{f['check']}** ({f['severity']})  \n{f['message']}")

        st.subheader("AI diagnosis")
        diagnosis = diagnose(case, findings)
        st.write(f"**Root cause:** {diagnosis['root_cause']}")
        st.write(f"**Confidence:** {diagnosis['confidence']}%")
        st.write(f"**OSI layer:** {diagnosis['osi_layer']}")
        st.write(f"**Next command:** `{diagnosis['next_command']}`")
        with st.expander("Evidence cited by AI"):
            for e in diagnosis["evidence"]:
                st.write(f"- {e}")
        with st.expander("Recommended fix steps (never auto-applied)"):
            for step in diagnosis["fix_steps"]:
                st.write(f"- {step}")

        st.subheader("Human review")
        existing = next((r for r in reviews if r["case_id"] == case_id), None)
        if existing:
            st.write(f"**Decision:** {existing['reviewer_decision']}")
            st.write(f"**Final diagnosis:** {existing['final_diagnosis']}")
            if existing.get("reason_for_correction"):
                st.write(f"**Reason:** {existing['reason_for_correction']}")
        else:
            st.warning(
                "No human review recorded yet for this case. Run "
                "`python3 src/main.py --case " + case_id + "` in a terminal "
                "to perform an interactive Accept/Edit/Reject review."
            )


def main():
    st.title("🛰️ NetSage AI — Troubleshooting Dashboard")
    st.caption(
        "AI-assisted, evidence-grounded network fault diagnosis with "
        "mandatory human review. Nothing here ever auto-applies a fix."
    )

    cases = _load_cases()
    reviews = load_reviews()

    tabs = st.tabs(["Overview", "Issue Analysis", "Severity", "Responsible AI", "Case Detail"])
    with tabs[0]:
        render_overview(cases, reviews)
    with tabs[1]:
        render_issue_analysis(cases)
    with tabs[2]:
        render_severity(cases)
    with tabs[3]:
        render_responsible_ai(reviews)
    with tabs[4]:
        render_case_detail(cases, reviews)


if __name__ == "__main__":
    main()
