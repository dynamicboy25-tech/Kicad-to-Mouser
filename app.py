import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Hardware BOM Reformatter", page_icon="⚡", layout="centered"
)

st.title("⚡ KiCad & Excel to Mouser BOM")
st.markdown(
    "Upload your **KiCad XML BOM export** (`.xml`) or an **Excel file** to instantly generate a clean import file for Mouser."
)

uploaded_file = st.file_uploader(
    "Choose a file", type=["xlsx", "xls", "xml"]
)

if uploaded_file is not None:
  file_extension = uploaded_file.name.split(".")[-1].lower()
  df = None

  try:
    if file_extension in ["xlsx", "xls"]:
      df = pd.read_excel(uploaded_file)
      st.success("Excel file successfully loaded!")

    elif file_extension == "xml":
      # Parse KiCad XML BOM
      tree = ET.parse(uploaded_file)
      root = tree.getroot()

      components = []
      for comp in root.findall(".//components/component"):
        ref = comp.get("ref")
        value = (
            comp.find("value").text if comp.find("value") is not None else ""
        )
        footprint = (
            comp.find("footprint").text
            if comp.find("footprint") is not None
            else ""
        )

        # Extract fields (looking for part numbers)
        fields_dict = {}
        fields_elem = comp.find("fields")
        if fields_elem is not None:
          for field in fields_elem.findall("field"):
            field_name = field.get("name")
            fields_dict[field_name] = field.text

        components.append({
            "Reference": ref,
            "Value": value,
            "Footprint": footprint,
            **fields_dict,
        })

      raw_df = pd.DataFrame(components)
      st.success(
          f"KiCad XML successfully parsed! Found {len(raw_df)} components."
      )
      st.write("### Raw Components Preview:")
      st.dataframe(raw_df.head())

      # Field mapping for KiCad
      st.write("---")
      st.write("### Select Part Number Field")
      available_fields = raw_df.columns.tolist()

      # Try to guess the part number field
      default_idx = 0
      for candidate in [
          "MFG_PN",
          "Manufacturer Part Number",
          "Mouser",
          "Part Number",
          "Value",
      ]:
        if candidate in available_fields:
          default_idx = available_fields.index(candidate)
          break

      mpn_field = st.selectbox(
          "Column/Field containing the Manufacturer Part Number",
          available_fields,
          index=default_idx,
      )

      # Group identical parts to calculate quantities
      grouped = (
          raw_df.groupby(mpn_field)
          .size()
          .reset_index(name="Quantity")
          .rename(columns={mpn_field: "Manufacturer Part Number"})
      )
      # Reorder columns for Mouser
      df = grouped[["Quantity", "Manufacturer Part Number"]]

    if df is not None and file_extension in ["xlsx", "xls"]:
      st.write("### Preview of Raw Data:")
      st.dataframe(df.head())

      columns = df.columns.tolist()
      col1, col2 = st.columns(2)
      with col1:
        qty_col = st.selectbox(
            "Quantity Column",
            columns,
            index=0 if "Quantity" not in columns else columns.index("Quantity"),
        )
      with col2:
        mpn_col = st.selectbox(
            "Part Number Column",
            columns,
            index=(
                1
                if len(columns) > 1 and "Part Number" not in columns
                else (
                    columns.index("Part Number")
                    if "Part Number" in columns
                    else 0
                )
            ),
        )

      df = pd.DataFrame({
          "Quantity": df[qty_col],
          "Manufacturer Part Number": df[mpn_col],
      })

    if st.button("Generate Mouser BOM"):
      df["Manufacturer Part Number"] = (
          df["Manufacturer Part Number"].astype(str).str.strip()
      )

      st.write("---")
      st.write("### Formatted BOM Preview for Mouser:")
      st.dataframe(df)

      csv_data = df.to_csv(index=False).encode("utf-8")

      st.download_button(
          label="📥 Download Formatted CSV for Mouser",
          data=csv_data,
          file_name="mouser_bom_import.csv",
          mime="text/csv",
      )

  except Exception as e:
    st.error(f"Error processing file: {e}")
