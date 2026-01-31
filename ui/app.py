import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI Resume Reviewer (Local)", page_icon="🧠", layout="centered")
st.title("🧠 AI Resume Reviewer Agent (Local Build with Ollama)")
st.caption("Runs on Ollama locally. Upload resume → get structured feedback.")

with st.sidebar:
    st.header("Settings")
    target_role = st.text_input("Target role", "Backend Software Engineer")
    model = st.text_input("Ollama model", "mistral")
    st.markdown("---")
    st.write("Backend:", API_URL)

uploaded = st.file_uploader("Upload resume (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"])

if uploaded:
    if st.button("Review Resume"):
        with st.spinner("Reviewing..."):
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            data = {"target_role": target_role, "model": model}
            r = requests.post(f"{API_URL}/review", files=files, data=data, timeout=180)

        if r.status_code != 200:
            st.error(f"Error {r.status_code}: {r.text}")
        else:
            result = r.json()

            st.subheader(f"Score: {result.get('score', 0)}/100")
            st.write(result.get("summary", ""))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### ✅ Strengths")
                for s in result.get("strengths", []):
                    st.write(f"- {s}")
            with col2:
                st.markdown("### ⚠️ Gaps")
                for g in result.get("gaps", []):
                    st.write(f"- {g}")

            st.markdown("### 🧩 Missing ATS Keywords")
            kws = result.get("ats_keywords_missing", [])
            if kws:
                st.write(", ".join(kws))
            else:
                st.write("None detected (or model did not return keywords).")

            st.markdown("### ✍️ Bullet Rewrites")
            for br in result.get("bullet_rewrites", []):
                st.markdown("**Original:**")
                st.write(br.get("original", ""))
                st.markdown("**Improved:**")
                st.write(br.get("improved", ""))
                st.caption(br.get("why", ""))

            rf = result.get("role_fit", {})
            st.markdown("### 🎯 Role Fit")
            st.write(f"**Target Role:** {rf.get('target_role', '')}")
            st.write(f"**Fit Level:** {rf.get('fit_level', '')}")
            st.write(rf.get("why", ""))

            st.markdown("### 📅 Next Actions (7 days)")
            for a in result.get("next_actions_7_days", []):
                st.write(f"- {a}")
