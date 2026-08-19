import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. تنظیمات اولیه صفحه
st.set_page_config(page_title="نرم‌افزار مدیریت نماز", page_icon="🕌", layout="wide")

# 2. اتصال هوشمند به سرورهای گوگل از طریق Secrets
@st.cache_resource
def get_google_connection():
    info = dict(st.secrets["gcp_service_account"])
    
    pk = str(info["private_key"])
    if "\\n" in pk:
        pk = pk.replace("\\n", "\n")
    info["private_key"] = pk

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key('1pq6IE2MIdLh6uXRaYGEsAKYxekQHlStPNn7Liu4kKL4')
    return sh

def load_data_from_google(sheet_index):
    sh = get_google_connection()
    ws = sh.get_worksheet(sheet_index)
    data = ws.get_all_values()
    if len(data) > 0:
        return pd.DataFrame(data[1:], columns=data[0])
    return pd.DataFrame()

# 3. طراحی منوی کناری
st.sidebar.title("📿 منوی اصلی")
menu = st.sidebar.radio(
    "لطفاً یک بخش را انتخاب کنید:",
    ["🏠 خانه (داشبورد)", "⚙️ تنظیمات و محاسبه", "📅 ردیاب روزانه", "👤 قضای شخصی", "🤝 استیجاری"]
)

st.title("🕌 نرم‌افزار هوشمند مدیریت نماز (نسخه ابری)")
st.markdown("---")

# 4. بدنه اصلی برنامه
try:
    sh = get_google_connection()
    st.sidebar.success("☁️ متصل به دیتابیس ابری گوگل")
    
    if menu == "🏠 خانه (داشبورد)":
        st.subheader("🕌 داشبورد گرافیکی و وضعیت کلی شما")
        st.info("ارتباط با دیتابیس گوگل برقرار است. خلاصه وضعیت شما به شرح زیر است:")
        st.markdown("---")
        
        try:
            df_personal = load_data_from_google(2) # شیت سوم: قضای شخصی
            
            sobh_total = pd.to_numeric(df_personal.iloc[6:, 1], errors='coerce').sum()
            zohr_total = pd.to_numeric(df_personal.iloc[6:, 2], errors='coerce').sum()
            asr_total = pd.to_numeric(df_personal.iloc[6:, 3], errors='coerce').sum()
            maghrib_total = pd.to_numeric(df_personal.iloc[6:, 4], errors='coerce').sum()
            isha_total = pd.to_numeric(df_personal.iloc[6:, 5], errors='coerce').sum()
            
            dor_kamel = min(sobh_total, zohr_total, asr_total, maghrib_total, isha_total)
            
            col1, col2, col3 = st.columns(3)
            col1.metric(label="🏆 شبانه‌روزهای کامل (دور کامل)", value=f"{int(dor_kamel)} روز")
            col2.metric(label="📊 مجموع نمازهای خوانده شده", value=f"{int(sobh_total+zohr_total+asr_total+maghrib_total+isha_total)} وعده")
            col3.metric(label="🌟 بیشترین پیشرفت", value=f"{int(max([sobh_total, zohr_total, asr_total, maghrib_total, isha_total]))}")
            
            st.markdown("### 📈 نمودار وضعیت نمازهای قضای خوانده شده")
            chart_data = pd.DataFrame({
                "وعده نماز": ["صبح", "ظهر", "عصر", "مغرب", "عشا"],
                "تعداد خوانده شده": [sobh_total, zohr_total, asr_total, maghrib_total, isha_total]
            })
            st.bar_chart(chart_data.set_index("وعده نماز"), color="#4CAF50")
            
        except Exception as e:
            st.warning("⚠️ برای نمایش نمودار، لطفاً ابتدا چند نماز قضا در دیتابیس ثبت کنید.")

    elif menu == "⚙️ تنظیمات و محاسبه":
        st.subheader("⚙️ ماشین حسابِ دقیقِ بدهیِ نماز")
        with st.form("calc_form"):
            st.markdown("#### 📅 اطلاعات تاریخ")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**تاریخ شروع (سن تکلیف):**")
                c1, c2, c3 = st.columns(3)
                start_y = c1.number_input("سال", min_value=1300, max_value=1500, value=1369, key="sy")
                start_m = c2.number_input("ماه", min_value=1, max_value=12, value=1, key="sm")
                start_d = c3.number_input("روز", min_value=1, max_value=31, value=1, key="sd")
            with col2:
                st.write("**تاریخ امروز:**")
                t1, t2, t3 = st.columns(3)
                end_y = t1.number_input("سال ", min_value=1300, max_value=1500, value=1403, key="ey")
                end_m = t2.number_input("ماه ", min_value=1, max_value=12, value=1, key="em")
                end_d = t3.number_input("روز ", min_value=1, max_value=31, value=1, key="ed")
                
            calculate_btn = st.form_submit_button("🧮 محاسبه دقیق بدهی")
            
            if calculate_btn:
                def calc_days(y, m, d):
                    if m <= 6: days_in_months = (m - 1) * 31 + d
                    else: days_in_months = 186 + (m - 7) * 30 + d
                    return (y * 365) + int(y / 4) + days_in_months
                
                total_debt = calc_days(end_y, end_m, end_d) - calc_days(start_y, start_m, start_d)
                
                if total_debt < 0:
                    st.error("❌ تاریخ امروز نمی‌تواند قبل از تاریخ شروع باشد!")
                else:
                    st.success(f"✅ دقیقاً **{total_debt:,} روز** از آن تاریخ گذشته است.")
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; background-color:#1E1E1E; padding:20px; border-radius:10px; text-align:center;'>
                        <div><h3 style='color:#4CAF50;'>🌅 صبح</h3><p style='font-size:20px;'>{total_debt:,}</p></div>
                        <div><h3 style='color:#FFC107;'>☀️ ظهر</h3><p style='font-size:20px;'>{total_deb
