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
                        <div><h3 style='color:#FFC107;'>☀️ ظهر</h3><p style='font-size:20px;'>{total_debt:,}</p></div>
                        <div><h3 style='color:#2196F3;'>🌤 عصر</h3><p style='font-size:20px;'>{total_debt:,}</p></div>
                        <div><h3 style='color:#FF5722;'>🌇 مغرب</h3><p style='font-size:20px;'>{total_debt:,}</p></div>
                        <div><h3 style='color:#9C27B0;'>🌃 عشا</h3><p style='font-size:20px;'>{total_debt:,}</p></div>
                    </div>
                    """, unsafe_allow_html=True)

    elif menu == "📅 ردیاب روزانه":
        st.subheader("📅 ثبت و ویرایش وضعیت ردیاب روزانه")
        st.caption("💡 نکته: اگر تاریخی که وارد می‌کنید قبلاً ثبت شده باشد، اطلاعات همان تاریخ به‌روزرسانی (ویرایش) خواهد شد.")
        
        with st.form("daily_form", clear_on_submit=True):
            tarikh = st.text_input("تاریخ امروز (مثال: 1403/06/15)", placeholder="1403/06/15")
            vaziat = ["اول وقت", "زمان واجب", "قضا شده", "نخوانده"]
            col_s, col_z, col_a, col_m, col_e = st.columns(5)
            with col_s: sobh = st.selectbox("🌅 صبح", vaziat)
            with col_z: zohr = st.selectbox("☀️ ظهر", vaziat)
            with col_a: asr = st.selectbox("🌤 عصر", vaziat)
            with col_m: maghrib = st.selectbox("🌇 مغرب", vaziat)
            with col_e: isha = st.selectbox("🌃 عشا", vaziat)
            
            submitted = st.form_submit_button("☁️ ثبت / ویرایش در سرور گوگل")
            
            if submitted:
                if tarikh.strip() == "": 
                    st.error("❌ لطفاً تاریخ را وارد کنید.")
                else:
                    try:
                        ws = sh.get_worksheet(1)
                        col_a_vals = ws.col_values(1)
                        
                        # بررسی اینکه آیا این تاریخ قبلاً ثبت شده یا خیر
                        if tarikh in col_a_vals:
                            target_row = col_a_vals.index(tarikh) + 1
                            is_edit = True
                        else:
                            target_row = max(2, len(col_a_vals) + 1)
                            is_edit = False
                        
                        ws.update(values=[[tarikh]], range_name=f'A{target_row}')
                        ws.update(values=[[sobh, zohr, asr, maghrib, isha]], range_name=f'C{target_row}:G{target_row}')
                        
                        if is_edit:
                            st.success(f"✏️ اطلاعات تاریخ **{tarikh}** با موفقیت ویرایش و به‌روزرسانی شد!")
                        else:
                            st.success(f"✅ اطلاعات تاریخ **{tarikh}** با موفقیت در دیتابیس ابری ثبت شد!")
                    except Exception as e: 
                        st.error(f"❌ خطای اتصال به گوگل: {e}")
        
        st.markdown("### 📊 تاریخچه ثبت‌ها")
        st.dataframe(load_data_from_google(1), use_container_width=True)

    elif menu == "👤 قضای شخصی":
        st.subheader("👤 ثبت نمازهای قضای خوانده شده")
        with st.form("qaza_form", clear_on_submit=True):
            tarikh = st.text_input("تاریخ خواندن قضا (مثال: 1403/06/15)", placeholder="1403/06/15")
            c_s, c_z, c_a, c_m, c_e = st.columns(5)
            with c_s: sobh = st.number_input("🌅 صبح", min_value=0, step=1)
            with c_z: zohr = st.number_input("☀️ ظهر", min_value=0, step=1)
            with c_a: asr = st.number_input("🌤 عصر", min_value=0, step=1)
            with c_m: maghrib = st.number_input("🌇 مغرب", min_value=0, step=1)
            with c_e: isha = st.number_input("🌃 عشا", min_value=0, step=1)
                
            submitted = st.form_submit_button("☁️ ثبت در سرور گوگل")
            
            if submitted:
                if tarikh == "": st.error("❌ لطفاً تاریخ را وارد کنید.")
                elif (sobh + zohr + asr + maghrib + isha) == 0: st.warning("⚠️ شما هیچ نمازی را وارد نکرده‌اید.")
                else:
                    try:
                        ws = sh.get_worksheet(2)
                        col_a = ws.col_values(1)
                        empty_row = max(8, len(col_a) + 1)
                        ws.update(values=[[tarikh]], range_name=f'A{empty_row}')
                        ws.update(values=[[sobh, zohr, asr, maghrib, isha]], range_name=f'B{empty_row}:F{empty_row}')
                        st.success(f"✅ دست مریزاد! آمار شما با موفقیت در اینترنت ذخیره شد.")
                    except Exception as e: st.error(f"❌ خطای اتصال به گوگل: {e}")

        st.markdown("### 📊 تاریخچه ثبت‌شده‌ها")
        ws_qaza = sh.get_worksheet(2)
        qaza_data = ws_qaza.get_all_values()
        
        if len(qaza_data) > 6:
            df_personal = pd.DataFrame(qaza_data[7:], columns=qaza_data[6])
            
            # حذف ستون‌های بدون نام
            df_personal = df_personal.loc[:, df_personal.columns != '']
            
            st.dataframe(df_personal, use_container_width=True)
        else:
            st.info("هنوز هیچ قضایی در دفترچه پایین ثبت نشده است.")

    elif menu == "🤝 استیجاری":
        st.subheader("🤝 ثبت و مدیریت نمازهای استیجاری")
        
        df_estijari = load_data_from_google(3)
        raw_names = df_estijari.iloc[0:30, 0].tolist()
        names_list = [name for name in raw_names if str(name).strip() != '']
        
        if len(names_list) == 0:
            st.warning("⚠️ نام شخصی یافت نشد. لطفاً در گوگل شیت خود، در داشبورد بالا یک نام اضافه کنید.")
        else:
            with st.form("estijari_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1: tarikh = st.text_input("تاریخ خواندن (مثال: 1403/06/15)", placeholder="1403/06/15")
                with col2: shakhs = st.selectbox("نام شخص (قرارداد)", names_list)
                
                c_s, c_z, c_a, c_m, c_e = st.columns(5)
                with c_s: sobh = st.number_input("🌅 صبح", min_value=0, step=1, key="e_s")
                with c_z: zohr = st.number_input("☀️ ظهر", min_value=0, step=1, key="e_z")
                with c_a: asr = st.number_input("🌤 عصر", min_value=0, step=1, key="e_a")
                with c_m: maghrib = st.number_input("🌇 مغرب", min_value=0, step=1, key="e_m")
                with c_e: isha = st.number_input("🌃 عشا", min_value=0, step=1, key="e_e")
                    
                submitted = st.form_submit_button("☁️ ثبت برای این شخص در گوگل")
                
                if submitted:
                    if tarikh == "": st.error("❌ لطفاً تاریخ را وارد کنید.")
                    elif (sobh + zohr + asr + maghrib + isha) == 0: st.warning("⚠️ حداقل یک نماز را وارد کنید.")
                    else:
                        try:
                            ws = sh.get_worksheet(3)
                            col_a = ws.col_values(1)
                            empty_row = max(36, len(col_a) + 1)
                            ws.update(values=[[tarikh]], range_name=f'A{empty_row}')
                            ws.update(values=[[shakhs, sobh, zohr, asr, maghrib, isha]], range_name=f'C{empty_row}:H{empty_row}')
                            st.success(f"✅ عالی! نمازها برای {shakhs} مستقیماً در گوگل شیت ذخیره شد.")
                        except Exception as e: st.error(f"❌ خطای اتصال به گوگل: {e}")
        
        st.markdown("---")
        st.markdown("### 📊 تاریخچه ثبت‌شده‌ها (استیجاری)")
        ws_estijari = sh.get_worksheet(3)
        estijari_data = ws_estijari.get_all_values()
        
        if len(estijari_data) > 34:
            df_updated = pd.DataFrame(estijari_data[35:], columns=estijari_data[34])
            df_updated = df_updated.loc[:, df_updated.columns != '']
            st.dataframe(df_updated, use_container_width=True)
        else:
            st.info("هنوز هیچ نمازی در دفترچه پایین ثبت نشده است.")

except Exception as e:
    st.error(f"❌ ارتباط با سرور گوگل برقرار نشد! خطای زیر را بررسی کنید:\n\n{e}")
