import streamlit as st
from src.i18n import t

_COPY_BUTTON = st.components.v2.component(
    "copy_button",
    html="<button id='copy-btn' type='button'></button>",
    css="""
button {
  font-family: inherit;
  font-size: var(--st-font-size, 14px);
  color: var(--st-text-color);
  background-color: var(--st-secondary-background-color);
  border: 1px solid var(--st-border-color, rgba(49, 51, 63, 0.2));
  border-radius: var(--st-border-radius, 8px);
  padding: 0.25rem 0.75rem;
  cursor: pointer;
}
button:hover {
  border-color: var(--st-primary-color);
  color: var(--st-primary-color);
}
""",
    js="""
export default function (component) {
  const { data, parentElement, setTriggerValue } = component
  const btn = parentElement.querySelector('#copy-btn')
  if (!btn) return
  btn.textContent = data?.label ?? 'Copy'
  btn.onclick = () => {
    const text = data?.value ?? ''
    // navigator.clipboard is missing on non-https pages and some mobile webviews.
    const fallback = () => {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.setAttribute('readonly', '')  // no keyboard pop-up on iOS
      ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;font-size:16px'  // 16px: no iOS zoom
      document.body.appendChild(ta)  // body, not the shadow root: iOS can't select inside shadow DOM
      ta.select()
      ta.setSelectionRange(0, text.length)  // iOS ignores select()
      const ok = document.execCommand('copy')
      ta.remove()
      if (ok) setTriggerValue('copied', true)
    }
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(() => setTriggerValue('copied', true), fallback)
    } else {
      fallback()
    }
  }
}
""",
)


def copy_button(label, value, key):
    result = _COPY_BUTTON(
        key=key,
        data={"label": label, "value": value},
        on_copied_change=lambda: None,
    )
    if result.copied:
        st.toast(t("Copied to clipboard"))
