import celebtwin_ui.main
import celebtwin_ui.playground
import streamlit as st


def main():
    page = st.navigation([
        st.Page(
            celebtwin_ui.main.main, default=True,
            title="Ton jumeau célèbre – Celebtwin", icon="👯‍♂️"),
        st.Page(
            celebtwin_ui.playground.main, url_path="playground",
            title="Playground – Celebtwin", icon="🧪"),
    ])
    page.run()


if __name__ == "__main__":
    main()
