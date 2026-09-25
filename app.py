"""
Voice-to-Insight AI Agent
--------------------------
Record your voice -> transcribe locally with Whisper -> understand intent
with a local LLM (Ollama/Qwen) -> store it as a "mission" you can browse and
manage -> optionally push it straight into a Notion database.

Run with: streamlit run app.py
"""

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from streamlit_mic_recorder import mic_recorder

from core.transcribe import load_whisper_model, transcribe_audio
from core.analyze import analyze_text
from core.storage import add_mission, load_missions, update_mission, delete_mission
from core.notion_sync import notion_configured, push_to_notion

st.set_page_config(page_title="Voice-to-Insight AI Agent", page_icon="🎙️", layout="wide")

st.title("🎙️ المساعد الصوتي الذكي (Local Whisper + Qwen + Notion)")
st.caption("سجّلي صوتك، Whisper يفرّغه محلياً، Qwen يحلله، ثم يُحفظ كمهمة يمكنك متابعتها أو إرسالها إلى Notion.")

# ---------------------------------------------------------------------------
# Sidebar: mission log (this is what lets you "come back and see your
# missions easily" instead of losing every result the moment you refresh).
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🗂️ سجل المهام (Missions)")
    missions = load_missions()

    if not missions:
        st.info("لا توجد مهام محفوظة بعد. سجّلي أول جملة لتبدأ القائمة.")
    else:
        intent_filter = st.multiselect(
            "تصفية حسب النوع",
            options=["task", "content_creation"],
            default=["task", "content_creation"],
        )
        show_done = st.checkbox("عرض المهام المنجزة", value=True)

        priority_order = {"high": 0, "medium": 1, "low": 2}
        filtered = [
            m for m in missions
            if m.get("intent") in intent_filter and (show_done or not m.get("done"))
        ]
        filtered.sort(
            key=lambda m: (priority_order.get(m.get("priority", "medium"), 1), m["created_at"]),
        )

        st.caption(f"{len(filtered)} / {len(missions)} مهمة")

        for m in filtered:
            status_icon = "✅" if m.get("done") else "🔲"
            with st.expander(f"{status_icon} [{m.get('priority', 'medium').upper()}] {m['title']}"):
                st.write(m.get("summary_or_caption", ""))
                st.caption(
                    f"🗓️ {m['created_at']} · 🎯 {m.get('intent')} · 📌 {m.get('action_platform', '-')}"
                )
                c1, c2, c3 = st.columns(3)
                if c1.button("✔️ تم", key=f"done_{m['id']}"):
                    update_mission(m["id"], {"done": not m.get("done", False)})
                    st.rerun()
                if c2.button("🗑️ حذف", key=f"del_{m['id']}"):
                    delete_mission(m["id"])
                    st.rerun()
                if notion_configured():
                    if m.get("notion_page_id"):
                        c3.markdown("🟢 في Notion")
                    elif c3.button("📤 أرسل", key=f"push_{m['id']}"):
                        page_id = push_to_notion(m)
                        if page_id:
                            update_mission(m["id"], {"notion_page_id": page_id})
                            st.success("تم الإرسال إلى Notion")
                            st.rerun()
                        else:
                            st.error("فشل الإرسال، تحقق من إعدادات Notion.")

    st.divider()
    if not notion_configured():
        st.warning("Notion غير مُفعّل. أضيفي NOTION_TOKEN و NOTION_DATABASE_ID في ملف .env")
    else:
        st.success("Notion متصل ✅")

# ---------------------------------------------------------------------------
# Main: recorder + pipeline
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)

whisper_model = load_whisper_model()

with col1:
    st.header("🎛️ التسجيل")
    auto_sync = st.checkbox(
        "إرسال المهام تلقائياً إلى Notion عند التسجيل",
        value=False,
        disabled=not notion_configured(),
    )
    audio_record = mic_recorder(start_prompt="🎙️ ابدأ التسجيل", stop_prompt="⏹️ إنهاء", key="recorder")

    if audio_record:
        st.audio(audio_record["bytes"])

        with st.spinner("⏳ Whisper يفرّغ الصوت..."):
            text = transcribe_audio(whisper_model, audio_record["bytes"])

        if text.startswith("ERROR::"):
            st.error(text.replace("ERROR::", ""))
        else:
            st.success("✅ تم التفريغ")
            st.info(f"💬 {text}")

            with st.spinner("🧠 Qwen يحلل النية ويستخرج البيانات..."):
                insights = analyze_text(text)

            st.session_state["insights"] = insights
            st.session_state["current_text"] = text

            if "error" not in insights:
                mission = add_mission(text, insights)
                st.session_state["last_mission"] = mission
                if auto_sync and notion_configured():
                    page_id = push_to_notion(mission)
                    if page_id:
                        update_mission(mission["id"], {"notion_page_id": page_id})

with col2:
    st.header("💎 آخر تحليل")
    if "insights" in st.session_state:
        insights = st.session_state["insights"]
        if "error" in insights:
            st.error(insights["error"])
        else:
            st.caption(f"🎯 النص: \"{st.session_state.get('current_text', '')}\"")
            st.subheader("البيانات المهيكلة (JSON)")
            st.json(insights)

            intent = insights.get("intent", "task")
            platform = str(insights.get("action_platform", "notion")).upper()
            title = insights.get("title", "تحليل جديد")
            priority = str(insights.get("priority", "medium")).upper()

            if intent == "task":
                st.metric(label=f"📝 مهمة جديدة على [{platform}]", value=title)
                st.warning(f"🔥 الأولوية: {priority}")
            elif intent == "content_creation":
                st.success(f"📱 محتوى جاهز لمنصة [{platform}]")
                st.write(insights.get("summary_or_caption"))
            else:
                st.info(insights.get("summary_or_caption"))

            st.caption("✔️ تم حفظ هذه المهمة تلقائياً في سجل المهام على اليسار.")
    else:
        st.info("💡 سجّلي جملة لترى النتيجة هنا، وستُحفظ تلقائياً في سجل المهام على اليسار.")
