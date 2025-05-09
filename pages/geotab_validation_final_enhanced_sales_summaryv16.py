import streamlit as st
import io
import xlsxwriter
import pandas as pd
import re

# Must be first Streamlit command
st.set_page_config(page_title="Geotab Dashboard App", layout="wide")

st.title("📊 Geotab & Sales Validation App")

# ========== Utility Functions ==========

def extract_month_str(raw):
    match = re.search(r"\(([^)]+)\)", str(raw))
    return match.group(1) if match else None

def try_parse_month(s):
    for fmt in ("%b-%y", "%B-%y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except:
            continue
    return pd.NaT

def load_file(uploaded_file, file_type):
    try:
        if uploaded_file.name.endswith('.csv'):
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
            lines = stringio.readlines()
            header_row_index = next((i for i, line in enumerate(lines) if len(line.strip().split(',')) >= 5), None)
            df = pd.read_csv(io.StringIO("".join(lines)), skiprows=header_row_index, dtype=str, low_memory=False)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            st.error(f"Unsupported file type for {file_type}")
            return None, None
        df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)
        return df, "loaded"
    except Exception as e:
        st.error(f"Failed to load {file_type}: {e}")
        return None, None

def to_float(x):
    try:
        return float(x)
    except:
        return 0.0

# ========== File Uploaders ==========

sales_by_item_file = st.file_uploader("📂 Upload Sales By Item File", type=["csv", "xlsx"])
geotab_file = st.file_uploader("📂 Upload Geotab Billing File", type=["csv", "xlsx"])
crm_file = st.file_uploader("📂 Upload CRM File", type=["csv", "xlsx"])

growth_threshold = st.number_input("📈 Growth Warning Threshold (%)", min_value=0, max_value=500, value=40, step=5)
total_revenue = 0

# ========== Sales Section ==========

try:
    if sales_by_item_file:
        st.header("Filtered Sales Summary Metrics")
        sales_df, _ = load_file(sales_by_item_file, "Sales By Item")
        if sales_df is not None:
            if st.checkbox("Promote first row to header?", value=True):
                sales_df.columns = sales_df.iloc[0]
                sales_df = sales_df[1:].reset_index(drop=True)
                sales_df.columns = pd.Series(sales_df.columns).astype(str).str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)

            item_col = [col for col in sales_df.columns if "updated item name" in col][0]
            month_col = [col for col in sales_df.columns if "month" in col][0]
            amount_col = [col for col in sales_df.columns if "amount" in col][0]
            purchase_col = [col for col in sales_df.columns if "purchase price" in col][0]

            sales_df["parsed_month"] = sales_df[month_col].apply(extract_month_str).apply(try_parse_month).dt.to_period("M")

            selected_filters = st.multiselect("🔧 Filter Updated Item Names", ["MONTHLY FLEET", "MONTHLY CAMERA", "MONTHLY DATA"], default=["MONTHLY FLEET"])
            selected_months = st.multiselect("📅 Filter by Month", sorted(sales_df["parsed_month"].dropna().unique().tolist()))

            filtered_df = sales_df.copy()
            if selected_filters:
                filtered_df = filtered_df[filtered_df[item_col].fillna("").str.upper().str.startswith(tuple(selected_filters))]
            if selected_months:
                filtered_df = filtered_df[filtered_df["parsed_month"].isin(selected_months)]

            total_revenue = filtered_df[amount_col].apply(to_float).sum()
            total_purchase = filtered_df[purchase_col].apply(to_float).sum()
            growth_pct = 0

            if not filtered_df["parsed_month"].isna().all():
                monthly_revenue = (
                    filtered_df.groupby("parsed_month")[amount_col]
                    .apply(lambda x: x.apply(to_float).sum())
                    .sort_index()
                )
                if len(monthly_revenue) >= 4:
                    trailing_avg = monthly_revenue.iloc[-4:-1].mean()
                    current_month = monthly_revenue.iloc[-1]
                    growth_pct = round((current_month - trailing_avg) / trailing_avg * 100, 2) if trailing_avg > 0 else 0.0
                    st.metric("📉 Trailing 3-Month Avg Revenue", f"${trailing_avg:,.2f}")

            col1, col2 = st.columns(2)
            col1.metric("💵 Total Revenue", f"${total_revenue:,.2f}")
            col2.metric("📊 Growth %", f"{growth_pct:.2f}%")

            if growth_pct > growth_threshold:
                st.warning(f"🚨 Revenue grew {growth_pct:.2f}% vs trailing 3-month average of ${trailing_avg:,.2f}")

            if not filtered_df.empty:
                file_name = "billing_summary.csv"
                if selected_months:
                    month_labels = "_".join([str(m) for m in selected_months])
                    file_name = f"billing_summary_{month_labels}.csv"
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Billing Summary CSV", data=csv, file_name=file_name, mime="text/csv")

except Exception as e:
    st.error(f"💥 Error in Sales section: {e}")

# ========== Geotab Section ==========

try:
    if geotab_file and crm_file:
        st.header("📒 Geotab Billing Validation")
        geotab_df, _ = load_file(geotab_file, "Geotab")
        crm_df, _ = load_file(crm_file, "CRM")

        if geotab_df is not None and crm_df is not None:
            customer_col = [c for c in geotab_df.columns if "customer" in c][0]
            cost_col = [c for c in geotab_df.columns if "cost" in c or "price" in c or "amount" in c][0]
            serial_col = [c for c in geotab_df.columns if "serial" in c or "device" in c or "imei" in c or "number" in c][0]
            plan_col = [c for c in geotab_df.columns if "item" in c or "plan" in c or "product" in c][0]

            crm_serials = pd.concat([
                crm_df[col].dropna().astype(str).str.strip()
                for col in crm_df.columns if "serial" in col or "subscription name" in col or "device" in col
            ]).unique().tolist()

            geotab_serials_df = geotab_df[[customer_col, serial_col, plan_col, cost_col]].dropna()
            geotab_serials_df[serial_col] = geotab_serials_df[serial_col].astype(str).str.strip()
            geotab_serials_df = geotab_serials_df.drop_duplicates(subset=[customer_col, serial_col])
            geotab_serials_df["in_subscription"] = geotab_serials_df[serial_col].isin(crm_serials)

            validation_summary = geotab_serials_df.groupby(customer_col).agg(
                total_serials=('in_subscription', 'count'),
                missing_serials=('in_subscription', lambda x: (~x).sum())
            ).reset_index()
            validation_summary['% missing'] = (
                validation_summary['missing_serials'] / validation_summary['total_serials'] * 100
            ).round(2)

            geotab_summary = geotab_df.groupby(customer_col).agg(
                total_quantity=(serial_col, 'count'),
                total_cost=(cost_col, lambda x: pd.to_numeric(x, errors='coerce').sum())
            ).reset_index()

            final_summary = pd.merge(geotab_summary, validation_summary, on=customer_col, how="left")

            st.subheader("✅ Geotab Billing Summary and Serial Validation")
            st.dataframe(final_summary)

            total_serials = len(geotab_serials_df)
            verified_serials = geotab_serials_df["in_subscription"].sum()
            unverified_serials = total_serials - verified_serials
            percent_verified = round((verified_serials / total_serials) * 100, 2) if total_serials else 0
            percent_unverified = round(100 - percent_verified, 2)
            total_cost = pd.to_numeric(geotab_df[cost_col], errors='coerce').sum()
            unverified_cost = pd.to_numeric(
                geotab_serials_df[~geotab_serials_df["in_subscription"]][cost_col],
                errors='coerce'
            ).sum()
            percent_unverified_cost = round(unverified_cost / total_cost * 100, 2) if total_cost > 0 else 0
            margin = round(((total_revenue - total_cost) / total_revenue * 100), 2) if total_revenue else 0

            st.subheader("📊 Dashboard Metrics")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Serials", total_serials)
            col2.metric("Verified Serials", verified_serials)
            col3.metric("Unverified Serials", unverified_serials)
            col4, col5, col6 = st.columns(3)
            col4.metric("% Verified", f"{percent_verified}%")
            col5.metric("% Unverified", f"{percent_unverified}%")
            col6.metric("Total Cost", f"${total_cost:,.2f}")
            col7, col8, col9 = st.columns(3)
            col7.metric("Cost Needing Verification", f"${unverified_cost:,.2f}")
            col8.metric("% Cost At Risk", f"{percent_unverified_cost}%")
            col9.metric("Margin %", f"{margin}%")

            with st.expander("📤 Export Geotab Validation Summary"):
                dashboard_data = {
                    "Metric": [
                        "Total Serials", "Verified Serials", "Unverified Serials",
                        "% Verified", "% Unverified", "Total Cost",
                        "Cost Needing Verification", "% Cost At Risk", "Margin %", "Trailing 3-Month Avg Revenue"
                    ],
                    "Value": [
                        total_serials, verified_serials, unverified_serials,
                        f"{percent_verified}%", f"{percent_unverified}%", f"${total_cost:,.2f}",
                        f"${unverified_cost:,.2f}", f"{percent_unverified_cost}%", f"{margin}%",
                        f"${trailing_avg:,.2f}" if 'trailing_avg' in locals() else "N/A"
                    ]
                }

                dashboard_df = pd.DataFrame(dashboard_data)
                unverified_df = geotab_serials_df[~geotab_serials_df["in_subscription"]][[customer_col, serial_col, plan_col, cost_col]]
                cost_at_risk_df = unverified_df.groupby(customer_col).agg(
                    serials_missing=(serial_col, 'count'),
                    cost_at_risk=(cost_col, lambda x: pd.to_numeric(x, errors='coerce').sum())
                ).reset_index()

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    dashboard_df.to_excel(writer, sheet_name="Dashboard Summary", index=False)
                    final_summary.to_excel(writer, sheet_name="Geotab Serial Validation", index=False)
                    if 'filtered_df' in locals():
                        filtered_df.to_excel(writer, sheet_name="Billing Summary", index=False)
                    unverified_df.to_excel(writer, sheet_name="Unverified Serials", index=False)
                    cost_at_risk_df.to_excel(writer, sheet_name="Cost At Risk by Customer", index=False)

                st.download_button(
                    label="⬇️ Download Geotab Validation Summary",
                    data=output.getvalue(),
                    file_name="geotab_validation_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

except Exception as ge:
    st.error(f"❌ Geotab section failed: {ge}")
