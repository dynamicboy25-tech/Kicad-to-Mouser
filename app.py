import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="KiCad to Mouser BOM Exporter", page_icon="⚡", layout="centered"
)

st.title("⚡ KiCad XML to Mouser BOM")
st.markdown(
    "Upload your **KiCad XML BOM export** (`.xml`) to instantly aggregate parts, map your part numbers, and download a ready-to-use CSV for Mouser's Rapid BOM tool."
)

uploaded_file = st.file_uploader("Choose a KiCad XML file", type=["xml"])

if uploaded_file is not None:
  try:
    # Parse KiCad XML BOM
    tree = ET.parse(uploaded_file)
    root = tree.getroot()

    components = []
    for comp in root.findall(".//components/component"):
      ref = comp.get("ref")
      value = comp.find("value").text if comp.find("value") is not None else ""
      footprint = (
          comp.find("footprint").text
          if comp.find("footprint") is not None
          else ""
      )

      # Extract custom fields (where part numbers like Mouser or MFG PN are stored)
      fields_dict = {}
      fields_elem = comp.find("fields")
      if fields_elem is not None:
        for field in fields_elem.findall("field"):
          field_name = field.get("name")
          fields_dict[field_name] = field.text

      components.append(
          {"Reference": ref, "Value": value, "Footprint": footprint, **fields_dict}
      )

    raw_df = pd.DataFrame(components)
    st.success(
        f"KiCad XML successfully parsed! Found {len(raw_df)} total components."
    )

    st.write("### Raw Components Preview:")
    st.dataframe(raw_df.head())

    st.write("---")
    st.write("### Field Selection")
    available_fields = raw_df.columns.tolist()

    # Intelligently guess the part number field
    default_idx = 0
    for candidate in [
        "MFG_PN",
        "Manufacturer Part Number",
        "Mouser",
        "Mouser Part Number",
        "Part Number",
        "Value",
    ]:
      if candidate in available_fields:
        default_idx = available_fields.index(candidate)
        break

    mpn_field = st.selectbox(
        "Select the Field/Column containing your Manufacturer or Supplier Part Numbers:",
        available_fields,
        index=default_idx,
    )

    if st.button("Generate Mouser BOM"):
      # Clean data and group identical part numbers to sum quantities
      clean_df = raw_df.copy()
      clean_df[mpn_field] = clean_df[mpn_field].astype(str).str.strip()

      # Drop rows where part number is empty or nan
      clean_df = clean_df[
          clean_df[mpn_field].notna() & (clean_df[mpn_field] != "nan")
      ]

      grouped = (
          clean_df.groupby(mpn_field)
          .size()
          .reset_index(name="Quantity")
          .rename(columns={mpn_field: "Manufacturer Part Number"})
      )

      # Mouser expects Quantity first, then Part Number
      mouser_df = grouped[["Quantity", "Manufacturer Part Number"]]

      st.write("---")
      st.write("### Formatted BOM Preview for Mouser:")
      st.dataframe(mouser_df)

      csv_data = mouser_df.to_csv(index=False).encode("utf-8")

      st.download_button(
          label="📥 Download Formatted CSV for Mouser",
          data=csv_data,
          file_name="mouser_bom_import.csv",
          mime="text/csv",
      )

  except Exception as e:
    st.error(f"Error processing KiCad XML file: {e}")
