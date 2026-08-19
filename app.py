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

# تابع خواندن بدهی پایه ثبت‌شده از ماشین‌حساب
def get_base_debt():
    try:
        sh = get_google_connection()
        ws = sh.get_worksheet(2)
        val = ws.acell('B2').value
        if val and str(val).strip().isdigit():
            return int(str(val).strip())
        return 0
    except Exception:
        return 0

# تابع محاسبه دقیق بدهی‌ها از ردیاب روزانه (فقط "نخوانده")
def get_qaza_from_tracker():
    try:
        df_daily = load_data_from_google(1)
        if df_daily.empty or len(df_daily.columns) < 7:
            return {"sobh": 0, "zohr": 0, "asr": 0, "maghrib": 0, "isha": 0}
        
        qaza_statuses = ["نخوانده"]
        sobh = (df_daily.iloc[:, 2].astype(str).isin(qaza_statuses)).sum()
        zohr = (df_daily.iloc[:, 3].astype(str).isin(qaza_statuses)).sum()
        asr = (df_daily.iloc[:, 4].astype(str).isin(qaza_statuses)).sum()
        maghrib = (df_daily.iloc[:, 5].astype(str).isin(qaza_statuses)).sum()
        isha = (df_daily.iloc[:, 6].astype(str).isin(qaza_statuses)).sum()
        
        return {"sobh": sobh, "zohr": zohr, "asr": asr, "maghrib": maghrib, "isha": isha}
    except Exception:
        return {"sobh": 0, "zohr": 0, "asr": 0, "maghrib": maghrib, "isha": isha}

# تابع ثبت و بروزرسانی خلاصه‌ی آمارها مستقیماً در گوگل‌شیت
def sync_summary_to_google_sheet(sh):
    try:
        ws_qaza = sh.get_worksheet(2)
        base_debt = get_base_debt()
        q_tracker = get_qaza_from_tracker()
        
        data_qaza = ws_qaza.get_all_values()
        if len(data_qaza) > 6:
            df_p = pd.DataFrame(data_qaza[7:], columns=data_qaza[6])
            sobh_p = pd.to_numeric(df_p.iloc[:, 1], errors='coerce').sum()
            zohr_p = pd.to_numeric(df_p.iloc[:, 2], errors='coerce').sum()
            asr_p = pd.to_numeric(df_p.iloc[:, 3], errors='coerce').sum()
            maghrib_p = pd.to_numeric(df_p.iloc[:, 4], errors='coerce').sum()
            isha_p = pd.to_numeric(df_p.iloc[:, 5], errors='coerce').sum()
        else:
            sobh_p = zohr_p = asr_p = maghrib_p = isha_p = 0
            
        rem_s = max(0, int((base_debt + q_tracker["sobh"]) - sobh_p))
        rem_z = max(0, int((base_debt + q_tracker["zohr"]) - zohr_p))
        rem_a = max(0, int((base_debt + q_tracker["asr"]) - asr_p))
        rem_m = max(0, int((base_debt + q_tracker["maghrib"]) - maghrib_p))
        rem_i = max(0, int((base_debt + q_tracker["isha"]) - isha_p))
        
        # بروزرسانی خلاصه در ردیف‌های ۳ تا ۵ شیت قضای شخصی
        ws_qaza.update(values=[["نخوانده‌های ردیاب", q_tracker["sobh"], q_tracker["zohr"], q_tracker["asr"], q_tracker["maghrib"], q_tracker["isha"]]], range_name='A3:F3')
        ws_qaza.update(values=[["مجموع اداشده‌ها", int(sobh_p), int(zohr_p), int(asr_p), int(maghrib_p), int(isha_p)]], range_name='A4:F4')
        ws_qaza.update(values=[["صافی باقیمانده کل", rem_s, rem_z, rem_a, rem_m, rem_i]], range_name='A5:F5')
    except Exception:
        pass

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
            df_personal = load_data_from_google(2) # شیت قضای شخصی
            
            sobh_performed = pd.to_numeric(df_personal.iloc[6:, 1], errors='coerce').sum()
            zohr_performed = pd.to_numeric(df_personal.iloc[6:, 2], errors='coerce').sum()
            asr_performed = pd.to_numeric(df_personal.iloc[6:, 3], errors='coerce').sum()
            maghrib_performed = pd.to_numeric(df_personal.iloc[6:, 4], errors='coerce').sum()
            isha_performed = pd.to_numeric(df_personal.iloc[6:, 5], errors='coerce').sum()
            
            total_performed = int(sobh_performed + zohr_performed + asr_performed + maghrib_performed + isha_performed)
            dor_kamel = min(sobh_performed, zohr_performed, asr_performed, maghrib_performed, isha_performed)
            
            # آمار بدهی پایه و ردیاب روزانه
            base_debt_days = get_base_debt()
            q_tracker = get_qaza_from_tracker()
            total_unprayed = (base_debt_days * 5) + sum(q_tracker.values())
            
            # بدهی صافی مانده
            net_debt = max(0, total_unprayed - total_performed)
            
            col1, col2, col3 = st.columns(3)
            col1.metric(label="🏆 شبانه‌روزهای کامل اداشده (دور کامل)", value=f"{int(dor_kamel)} روز")
            col2.metric(label="📊 مجموع نمازهای قضای خوانده شده", value=f"{total_performed} وعده")
            col3.metric(label="🚨 صافی کل بدهی باقیمانده", value=f"{net_debt:,} وعده")
            
            # نوار پیشرفت ادا
            if total_unprayed > 0:
                progress_pct = min(100.0, (total_performed / total_unprayed) * 100)
                st.progress(progress_pct / 100, text=f"📈 درصد پیشرفت ادای کل بدهی‌ها: {progress_pct:.2f}%")
            
            st.markdown("### 📈 نمودار وضعیت نمازهای اداشده در برابر بدهی")
            chart_data = pd.DataFrame({
                "وعده نماز": ["صبح", "ظهر", "عصر", "مغرب", "عشا"],
                "قضای خوانده شده": [sobh_performed, zohr_performed, asr_performed, maghrib_performed, isha_performed],
                "کل بدهی (پایه + ردیاب)": [
                    base_debt_days + q_tracker["sobh"],
                    base_debt_days + q_tracker["zohr"],
                    base_debt_days + q_tracker["asr"],
                    base_debt_days + q_tracker["maghrib"],
                    base_debt_days + q_tracker["isha"]
                ]
            })
            st.bar_chart(chart_data.set_index("وعده نماز"))
            
        except Exception as e:
            st.warning("⚠️ برای نمایش نمودار، لطفاً ابتدا چند نماز قضا در دیتابیس ثبت کنید.")

    elif menu == "⚙️ تنظیمات و محاسبه":
        st.subheader("⚙️ ماشین حسابِ دقیقِ بدهیِ نماز")
        
        current_base = get_base_debt()
        if current_base > 0:
            st.info(f"📌 بدهی پایه تاریخیِ فعلی شما در دیتابیس: **{current_base:,} روز** ثبت شده است.")
            
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
                    st.session_state["calc_debt_result"] = total_debt

        if "calc_debt_result" in st.session_state:
            total_debt = st.session_state["calc_debt_result"]
            st.success(f"✅ دقیقاً **{total_debt:,} روز** از آن تاریخ گذشته است.")
            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
            col_s1.metric("🌅 صبح", f"{total_debt:,} روز")
            col_s2.metric("☀️ ظهر", f"{total_debt:,} روز")
            col_s3.metric("🌤 عصر", f"{total_debt:,} روز")
            col_s4.metric("🌇 مغرب", f"{total_debt:,} روز")
            col_s5.metric("🌃 عشا", f"{total_debt:,} روز")
            
            st.markdown("---")
            if st.button(f"💾 ذخیره این {total_debt:,} روز به عنوان «بدهی پایه تاریخی» من در دیتابیس"):
                try:
                    ws_qaza_base = sh.get_worksheet(2)
                    ws_qaza_base.update(values=[["بدهی پایه تاریخی", str(total_debt), str(total_debt), str(total_debt), str(total_debt), str(total_debt)]], range_name='A2:F2')
                    sync_summary_to_google_sheet(sh)
                    st.success(f"🎉 با موفقیت ثبت شد! عدد **{total_debt:,} روز** به‌عنوان بدهی پایه شما ذخیره و در گوگل شیت به‌روزرسانی شد.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطای ذخیره‌سازی: {e}")

    elif menu == "📅 ردیاب روزانه":
        st.subheader("📅 ثبت و ویرایش وضعیت ردیاب روزانه")
        st.caption("💡 نکته: اگر تاریخی که وارد می‌کنید قبلاً ثبت شده باشد، اطلاعات همان تاریخ به‌روزرسانی شده و موارد تکراری پاک می‌شوند.")
        
        ws_daily = sh.get_worksheet(1)
        
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
                        col_a_vals = ws_daily.col_values(1)
                        matching_rows = [i + 1 for i, val in enumerate(col_a_vals) if val == tarikh.strip()]
                        
                        if matching_rows:
                            target_row = matching_rows[0]
                            ws_daily.update(values=[[tarikh.strip()]], range_name=f'A{target_row}')
                            ws_daily.update(values=[[sobh, zohr, asr, maghrib, isha]], range_name=f'C{target_row}:G{target_row}')
                            
                            if len(matching_rows) > 1:
                                for dup_row in sorted(matching_rows[1:], reverse=True):
                                    ws_daily.delete_rows(dup_row)
                                st.success(f"✏️ اطلاعات تاریخ **{tarikh}** به‌روزرسانی شد و ردیف‌های تکراری اضافه پاک شدند!")
                            else:
                                st.success(f"✏️ اطلاعات تاریخ **{tarikh}** با موفقیت ویرایش و به‌روزرسانی شد!")
                        else:
                            target_row = max(2, len(col_a_vals) + 1)
                            ws_daily.update(values=[[tarikh.strip()]], range_name=f'A{target_row}')
                            ws_daily.update(values=[[sobh, zohr, asr, maghrib, isha]], range_name=f'C{target_row}:G{target_row}')
                            st.success(f"✅ اطلاعات تاریخ **{tarikh}** با موفقیت در دیتابیس ابری ثبت شد!")
                        
                        sync_summary_to_google_sheet(sh)
                    except Exception as e: 
                        st.error(f"❌ خطای اتصال به گوگل: {e}")

        with st.expander("🗑️ حذف یک تاریخ از دیتابیس (مدیریت تکراری‌ها یا اشتباهات)"):
            col_a_vals = ws_daily.col_values(1)
            existing_dates = list(set([d for d in col_a_vals[1:] if d.strip() != ""]))
            
            if existing_dates:
                date_to_delete = st.selectbox("تاریخ مورد نظر برای حذف را انتخاب کنید:", sorted(existing_dates, reverse=True))
                if st.button("❌ حذف کامل این تاریخ از دیتابیس"):
                    try:
                        rows_to_delete = [i + 1 for i, val in enumerate(col_a_vals) if val == date_to_delete]
                        for r_idx in sorted(rows_to_delete, reverse=True):
                            ws_daily.delete_rows(r_idx)
                        st.success(f"✅ تمام ثبت‌های مربوط به تاریخ **{date_to_delete}** با موفقیت حذف شدند!")
                        sync_summary_to_google_sheet(sh)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطا در حذف: {e}")
            else:
                st.info("هنوز هیچ تاریخی در دیتابیس ثبت نشده است.")
        
        st.markdown("### 📊 تاریخچه ثبت‌ها")
        st.dataframe(load_data_from_google(1), use_container_width=True)

    elif menu == "👤 قضای شخصی":
        st.subheader("👤 ثبت و مدیریت نمازهای قضای خوانده شده")
        
        ws_qaza = sh.get_worksheet(2)
        df_personal = load_data_from_google(2)
        
        # ۱. بدهی پایه تاریخی از ماشین حساب
        base_debt_days = get_base_debt()
        
        # ۲. مجموع خوانده‌شده‌ها در قضای شخصی
        sobh_p = pd.to_numeric(df_personal.iloc[6:, 1], errors='coerce').sum()
        zohr_p = pd.to_numeric(df_personal.iloc[6:, 2], errors='coerce').sum()
        asr_p = pd.to_numeric(df_personal.iloc[6:, 3], errors='coerce').sum()
        maghrib_p = pd.to_numeric(df_personal.iloc[6:, 4], errors='coerce').sum()
        isha_p = pd.to_numeric(df_personal.iloc[6:, 5], errors='coerce').sum()
        
        # ۳. نخوانده‌های جدید ردیاب روزانه
        q_tracker = get_qaza_from_tracker()
        
        # ۴. کل بدهی باقیمانده (پایه + ردیاب - خوانده‌شده)
        sobh_rem = max(0, int((base_debt_days + q_tracker["sobh"]) - sobh_p))
        zohr_rem = max(0, int((base_debt_days + q_tracker["zohr"]) - zohr_p))
        asr_rem = max(0, int((base_debt_days + q_tracker["asr"]) - asr_p))
        maghrib_rem = max(0, int((base_debt_days + q_tracker["maghrib"]) - maghrib_p))
        isha_rem = max(0, int((base_debt_days + q_tracker["isha"]) - isha_p))
        
        total_rem = sobh_rem + zohr_rem + asr_rem + maghrib_rem + isha_rem
        
        if total_rem > 0:
            st.warning(f"🚨 **خلاصه بدهی‌های باقیمانده (نمازهای «نخوانده» کسرشده با قضاهای اداشده - صافی مانده: {total_rem:,} وعده):**")
            col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns(5)
            col_q1.metric("🌅 صبح", f"{sobh_rem:,} وعده", delta=f"-{int(sobh_p):,} اداشده" if sobh_p > 0 else None)
            col_q2.metric("☀️ ظهر", f"{zohr_rem:,} وعده", delta=f"-{int(zohr_p):,} اداشده" if zohr_p > 0 else None)
            col_q3.metric("🌤 عصر", f"{asr_rem:,} وعده", delta=f"-{int(asr_p):,} اداشده" if asr_p > 0 else None)
            col_q4.metric("🌇 مغرب", f"{maghrib_rem:,} وعده", delta=f"-{int(maghrib_p):,} اداشده" if maghrib_p > 0 else None)
            col_q5.metric("🌃 عشا", f"{isha_rem:,} وعده", delta=f"-{int(isha_p):,} اداشده" if isha_p > 0 else None)
            st.caption("💡 هر زمان این نمازهای قضا را بجا آوردید، فرم زیر را پر کنید تا آمار اداشده‌های شما ثبت شده و از بدهی کسر گردد.")
            st.markdown("---")
        else:
            st.success("🎉 ماشاءالله! هیچ بدهی نماز قضایی برای شما ثبت نشده یا تمام بدهی‌ها ادا شده است.")
            st.markdown("---")

        with st.form("qaza_form", clear_on_submit=True):
            tarikh = st.text_input("تاریخ خواندن قضا (مثال: 1403/06/15)", placeholder="1403/06/15")
            c_s, c_z, c_a, c_m, c_e = st.columns(5)
            with c_s: sobh = st.number_input("🌅 صبح", min_value=0, step=1)
            with c_z: zohr = st.number_input("☀️ ظهر", min_value=0, step=1)
            with c_a: asr = st.number_input("🌤 عصر", min_value=0, step=1)
            with c_m: maghrib = st.number_input("🌇 مغرب", min_value=0, step=1)
            with c_e: isha = st.number_input("🌃 عشا", min_value=0, step=1)
                
            submitted = st.form_submit_button("☁️ ثبت / ویرایش در سرور گوگل")
            
            if submitted:
                if tarikh.strip() == "": 
                    st.error("❌ لطفاً تاریخ را وارد کنید.")
                elif (sobh + zohr + asr + maghrib + isha) == 0: 
                    st.warning("⚠️ شما هیچ عددی وارد نکرده‌اید.")
                else:
                    try:
                        col_a_qaza = ws_qaza.col_values(1)
                        matching_q_rows = [i + 1 for i, val in enumerate(col_a_qaza) if val == tarikh.strip() and i >= 7]
                        
                        if matching_q_rows:
                            target_row = matching_q_rows[0]
                            ws_qaza.update(values=[[tarikh.strip()]], range_name=f'A{target_row}')
                            ws_qaza.update(values=[[sobh, zohr, asr, maghrib, isha]], range_name=f'B{target_row}:F{target_row}')
                            
                            if len(matching_q_rows) > 1:
                                for dup_row in sorted(matching_q_rows[1:], reverse=True):
                                    ws_qaza.delete_rows(dup_row)
                                st.success(f"✏️ اطلاعات ثبت قضای تاریخ **{tarikh}** به‌روزرسانی شد و ردیف‌های تکراری پاک شدند!")
                            else:
                                st.success(f"✏️ اطلاعات ثبت قضای تاریخ **{tarikh}** با موفقیت ویرایش شد!")
                        else:
                            target_row = max(8, len(col_a_qaza) + 1)
                            ws_qaza.update(values=[[tarikh.strip()]], range_name=f'A{target_row}')
                            ws_qaza.update(values=[[sobh, zohr, asr, maghrib, isha]], range_name=f'B{target_row}:F{target_row}')
                            st.success("✅ دست مریزاد! آمار قضای شما با موفقیت در اینترنت ذخیره شد.")
                            
                        sync_summary_to_google_sheet(sh)
                    except Exception as e: 
                        st.error(f"❌ خطای اتصال به گوگل: {e}")

        # بخش حذف کادارهای اشتباه در قضای شخصی
        with st.expander("🗑️ حذف یا ویرایش یک تاریخ از لیست قضای شخصی (مدیریت اشتباهات)"):
            col_a_qaza = ws_qaza.col_values(1)
            existing_qaza_dates = list(set([d for i, d in enumerate(col_a_qaza) if i >= 7 and d.strip() != ""]))
            
            if existing_qaza_dates:
                qaza_date_to_delete = st.selectbox("تاریخ مورد نظر برای حذف را انتخاب کنید:", sorted(existing_qaza_dates, reverse=True), key="del_qaza_select")
                if st.button("❌ حذف کامل این تاریخ از قضای شخصی", key="del_qaza_btn"):
                    try:
                        rows_to_delete = [i + 1 for i, val in enumerate(col_a_qaza) if val == qaza_date_to_delete and i >= 7]
                        for r_idx in sorted(rows_to_delete, reverse=True):
                            ws_qaza.delete_rows(r_idx)
                        st.success(f"✅ تمام ثبت‌های مربوط به تاریخ **{qaza_date_to_delete}** از قضای شخصی حذف شدند!")
                        sync_summary_to_google_sheet(sh)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطا در حذف: {e}")
            else:
                st.info("هنوز هیچ تاریخی در قضای شخصی ثبت نشده است.")

        st.markdown("### 📊 تاریخچه ثبت‌شده‌ها")
        qaza_data = ws_qaza.get_all_values()
        
        if len(qaza_data) > 6:
            df_personal = pd.DataFrame(qaza_data[7:], columns=qaza_data[6])
            df_personal = df_personal.loc[:, df_personal.columns != '']
            st.dataframe(df_personal, use_container_width=True)
        else:
            st.info("هنوز هیچ قضایی در دفترچه پایین ثبت نشده است.")

    elif menu == "🤝 استیجاری":
        st.subheader("🤝 ثبت و مدیریت نمازهای استیجاری")
        
        ws_estijari = sh.get_worksheet(3)
        
        # ۱. کادر افزودن شخص / قرارداد جدید
        with st.expander("➕ افزودن نام شخص / قرارداد جدید"):
            with st.form("add_person_form", clear_on_submit=True):
                new_person = st.text_input("نام شخص / مرحوم جدید (مثال: مرحوم علی علوی)")
                btn_add_person = st.form_submit_button("➕ افزودن به لیست")
                
                if btn_add_person:
                    if new_person.strip() == "":
                        st.error("❌ لطفاً نام شخص را وارد کنید.")
                    else:
                        raw_col_a = ws_estijari.col_values(1)[:30]
                        existing_names = [n.strip() for n in raw_col_a if n.strip() != ""]
                        
                        if new_person.strip() in existing_names:
                            st.warning("⚠️ این نام قبلاً در لیست وجود دارد.")
                        else:
                            target_r = len(existing_names) + 1
                            if target_r > 30: target_r = 30
                            ws_estijari.update(values=[[new_person.strip()]], range_name=f'A{target_r}')
                            st.success(f"✅ نام **{new_person.strip()}** با موفقیت به لیست استیجاری اضافه شد!")
                            st.rerun()

        # ۲. خواندن لیست اسامی برای فرم ثبت
        df_estijari = load_data_from_google(3)
        raw_names = df_estijari.iloc[0:30, 0].tolist()
        names_list = [str(name).strip() for name in raw_names if str(name).strip() != '' and str(name).strip() != 'None']
        
        if len(names_list) == 0:
            st.info("💡 هنوز هیچ نامی در لیست استیجاری ثبت نشده است. لطفاً از کادر بالا (افزودن نام شخص جدید) اولین نام را اضافه کنید.")
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
                    if tarikh.strip() == "": 
                        st.error("❌ لطفاً تاریخ را وارد کنید.")
                    elif (sobh + zohr + asr + maghrib + isha) == 0: 
                        st.warning("⚠️ حداقل یک نماز را وارد کنید.")
                    else:
                        try:
                            col_a_est = ws_estijari.col_values(1)
                            empty_row = max(36, len(col_a_est) + 1)
                            ws_estijari.update(values=[[tarikh.strip()]], range_name=f'A{empty_row}')
                            ws_estijari.update(values=[[shakhs, sobh, zohr, asr, maghrib, isha]], range_name=f'C{empty_row}:H{empty_row}')
                            st.success(f"✅ عالی! نمازها برای **{shakhs}** مستقیماً در دیتابیس ذخیره شد.")
                        except Exception as e: 
                            st.error(f"❌ خطای اتصال به گوگل: {e}")
        
        # ۳. حذف یا ویرایش یک رکورد از تاریخچه استیجاری
        with st.expander("🗑️ حذف یا ویرایش یک ثبت از تاریخچه استیجاری (مدیریت اشتباهات)"):
            col_a_est = ws_estijari.col_values(1)
            existing_est_dates = list(set([d for i, d in enumerate(col_a_est) if i >= 35 and d.strip() != ""]))
            
            if existing_est_dates:
                est_date_to_delete = st.selectbox("تاریخ مورد نظر برای حذف را انتخاب کنید:", sorted(existing_est_dates, reverse=True), key="del_est_select")
                if st.button("❌ حذف کامل این تاریخ از استیجاری", key="del_est_btn"):
                    try:
                        rows_to_delete = [i + 1 for i, val in enumerate(col_a_est) if val == est_date_to_delete and i >= 35]
                        for r_idx in sorted(rows_to_delete, reverse=True):
                            ws_estijari.delete_rows(r_idx)
                        st.success(f"✅ تمام ثبت‌های مربوط به تاریخ **{est_date_to_delete}** از استیجاری حذف شدند!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطا در حذف: {e}")
            else:
                st.info("هنوز هیچ تاریخی در بخش استیجاری ثبت نشده است.")
        
        st.markdown("---")
        st.markdown("### 📊 تاریخچه ثبت‌شده‌ها (استیجاری)")
        estijari_data = ws_estijari.get_all_values()
        
        if len(estijari_data) > 34:
            df_updated = pd.DataFrame(estijari_data[35:], columns=estijari_data[34])
            df_updated = df_updated.loc[:, df_updated.columns != '']
            st.dataframe(df_updated, use_container_width=True)
        else:
            st.info("هنوز هیچ نمازی در دفترچه پایین ثبت نشده است.")

except Exception as e:
    st.error(f"❌ ارتباط با سرور گوگل برقرار نشد! خطای زیر را بررسی کنید:\n\n{e}")
