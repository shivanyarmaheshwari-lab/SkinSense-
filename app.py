
import streamlit as st
from PIL import Image

# Set the page configuration
st.set_page_config(page_title="Image Size Checker", page_icon="🖼️")

st.title("🖼️ Image Size Checker")
st.write("Upload a PNG or JPEG image below to view it and extract its width and height.")

# Create the file uploader widget
uploaded_file = st.file_uploader("Choose an image...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    try:
        # Open the image using PIL (Pillow)
        image = Image.open(uploaded_file)
       
        # Display the uploaded image
        st.image(image, caption="Uploaded Image", use_container_width=True)
       
        # Extract width and height
        width, height = image.size
       
        # Display the dimensions in a clean UI
        st.divider()
        st.subheader("📊 Image Dimensions")
       
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Width", value=f"{width} px")
        with col2:
            st.metric(label="Height", value=f"{height} px")
           
    except Exception as e:
        st.error(f"Error processing the image. Please make sure it's a valid image file. Details: {e}")
