import streamlit as st
import requests
from PIL import Image
import io

st.title("👯‍♂️ Trouve ton jumeau célèbre – CelebTwin")

# Image à upload
uploaded_file = st.file_uploader("📷 Upload une photo de toi", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Image chargée", use_container_width=True)

    # Bouton qui déclenche la prédiction
    if st.button("🔍 Qui est mon jumeau célèbre ?"):
        # Lecture du fichier image en mémoire
        image_bytes = uploaded_file.read()


        # ✅ URL de notre API
        api_url ="https://celebtwin-api-244684580447.europe-west4.run.app/predict"
        
        #"https://celebtwin-api-244684580447.europe-west4.run.app/predict"

        #"http://127.0.0.1:8000/predict"

          # ⚠️ Option : ajout d'un modèle dans les paramètres si nécessaire!
        params = {"model": "unused"}

        # Envoi de la requête
        files = {"file": (uploaded_file.name, image_bytes, uploaded_file.type)}
        try:
            response = requests.post(api_url, files=files)
            if response.status_code == 200:
                result = response.json()
                st.write("📦 Résultat brut de l’API :")
                st.json(result)

                #st.success(f"🎉 Ton jumeau célèbre est : **{result['result']}**")
            else:
                st.error("Erreur lors de la prédiction : code " + str(response.status_code))
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")
