import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="KiCad PCB to Full Mouser BOM Template",
    page_icon="⚡",
    layout="centered",
)

st.title("⚡ KiCad PCB to Full Mouser BOM Generator")
st.markdown(
    "Upload your native KiCad PCB file (`.kicad_pcb`). The app extracts all"
    " part numbers and quantities, then structures them into Mouser's exact"
    " multi-column BOM template layout."
)

uploaded_file = st.file_uploader("Choose a KiCad PCB file", type=["kicad_pcb"])

if uploaded_file is not None:
  try:
    content = uploaded_file.read().decode("utf-8")

    # Split content by footprint blocks to extract references and values
    footprint_blocks = content.split("(footprint ")
    components = []

    for block in footprint_blocks[1:]:
      ref_match = re.search(
          r'\(property\s+"Reference"\s+"(.*?)"', block, re.DOTALL
      )
      ref = ref_match.group(1) if ref_match else ""

      val_match = re.search(r'\(property\s+"Value"\s+"(.*?)"', block, re.DOTALL)
      val = val_match.group(1) if val_match else ""

      if ref:
        components.append({"Reference": ref, "Part Number": val})

    raw_df = pd.DataFrame(components)

    if not raw_df.empty:
      st.success(
          f"Successfully parsed PCB layout! Found {len(raw_df)} total"
          " components."
      )

      # Aggregate components by Part Number/Value to determine Order Quantity
      grouped = (
          raw_df.groupby("Part Number")
          .size()
          .reset_index(name="Order Quantity")
      )

      # Build the exact template structure matching Mouser's BOM Template
      template_columns = [
          "Mfr Part Number (Input)",
          "Manufacturer Part Number",
          "Mouser Part Number",
          "Manufacturer Name",
          "Description",
          "Quantity 1",
          "Unit Price 1",
          "Quantity 2",
          "Unit Price 2",
          "Quantity 3",
          "Unit Price 3",
          "Quantity 4",
          "Unit Price 4",
          "Quantity 5",
          "Unit Price 5",
          "Order Quantity",
          "Order Unit Price",
          "Min./Mult.",
          "Availability",
          "Lead Time in Days",
          "Lifecycle",
          "NCNR",
          "RoHS",
          "Pb Free",
          "Package Type",
          "Datasheet URL",
          "Product Image",
          "Design Risk",
      ]

      bom_df = pd.DataFrame(columns=template_columns)
      bom_df["Mfr Part Number (Input)"] = grouped["Part Number"]
      bom_df["Manufacturer Part Number"] = grouped["Part Number"]
      bom_df["Order Quantity"] = grouped["Order Quantity"]

      st.write("---")
      st.write("### Formatted BOM Template Preview:")
      st.dataframe(bom_df)

      # Export to Excel matching the template structure
      output_filename = "mouser_full_bom_template.xlsx"

      # Using pandas ExcelWriter to generate an Excel file
      @st.cache_data
      def convert_df_to_excel(df):
        from io import BytesIO

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
          df.to_excel(writer, index=False, sheet_name="Sheet1")
        return output.getvalue()

      excel_data = convert_df_to_excel(bom_df)

      st.download_button(
          label="📥 Download Filled Excel BOM Template",
          data=excel_data,
          file_name=output_filename,
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )
    else:
      st.warning("No component references found in this file.")

  except Exception as e:
    st.error(f"Error processing KiCad PCB file: {e}")
