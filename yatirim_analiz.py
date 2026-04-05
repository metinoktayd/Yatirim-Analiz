# app.py
import streamlit as st
from seasonality_table import get_returns_table
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime

# Sayfa ayarları
st.set_page_config(
    page_title="Yatırım Analizi",
    page_icon="💰",
    layout="wide"
)

# Ay çevirici
ay_cevir = {
    'Jan': 'Ocak', 'Feb': 'Şubat', 'Mar': 'Mart', 'Apr': 'Nisan',
    'May': 'Mayıs', 'Jun': 'Haziran', 'Jul': 'Temmuz', 'Aug': 'Ağustos',
    'Sep': 'Eylül', 'Oct': 'Ekim', 'Nov': 'Kasım', 'Dec': 'Aralık'
}

# Veri çek - cache ile hızlandır
@st.cache_data(ttl=3600)
def get_data(ticker, start, end):
    try:
        veri = get_returns_table(ticker, False, start, end)
        veri = veri.replace('-', np.nan)
        veri = veri.apply(pd.to_numeric, errors='coerce')
        veri.columns = [ay_cevir.get(col, col) for col in veri.columns]
        return veri
    except:
        return None

# Fiyat verileri çek
@st.cache_data(ttl=3600)
def get_price_data(ticker, start, end):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start, end=end, interval="1mo")
        
        if hist.empty:
            return None, None
        
        # Para birimi
        info = stock.info
        currency = info.get('currency', 'USD')
        currency_symbols = {
            'USD': '$', 'TRY': '₺', 'EUR': '€', 'GBP': '£', 'JPY': '¥'
        }
        symbol = currency_symbols.get(currency, currency)
        
        # Aylık fiyatları düzenle
        hist['Yil'] = hist.index.year
        hist['Ay'] = hist.index.month
        
        # Pivot tablo oluştur
        fiyat_pivot = hist.pivot_table(
            values='Close',
            index='Yil',
            columns='Ay',
            aggfunc='mean'
        )
        
        # Ay isimlerini değiştir
        ay_sirali = {
            1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan',
            5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos',
            9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
        }
        fiyat_pivot.columns = [ay_sirali.get(col, col) for col in fiyat_pivot.columns]
        
        return fiyat_pivot, symbol
    except:
        return None, None

# Güncel fiyat bilgisi
@st.cache_data(ttl=300)  # 5 dakika cache
def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        
        # Son fiyatı al
        hist = stock.history(period="5d")
        if hist.empty:
            return None, None, None
        
        current_price = hist['Close'].iloc[-1]
        
        # Döviz sembolü belirle
        info = stock.info
        currency = info.get('currency', 'USD')
        
        # Para birimi sembolü
        currency_symbols = {
            'USD': '$', 'TRY': '₺', 'EUR': '€', 'GBP': '£', 'JPY': '¥'
        }
        symbol = currency_symbols.get(currency, currency)
        
        # Değişim hesapla
        if len(hist) >= 2:
            prev_price = hist['Close'].iloc[-2]
            change = ((current_price - prev_price) / prev_price) * 100
        else:
            change = 0
        
        return current_price, symbol, change
    except:
        return None, None, None

def main():
    st.title("💰 Yatırım Ne Zaman Yapılmalı?")
    st.caption("Geçmiş verilere bakarak en uygun zamanları öğrenin")
    
    # Yan panel
    with st.sidebar:
        st.header("Ayarlar")
        
        # Ticker girişi
        st.subheader("📊 Yatırım Aracı")
        
        ticker = st.text_input(
            "Ticker Sembolü",
            placeholder="Örn: AAPL, BTC-USD, GC=F",
            help="Yahoo Finance ticker sembolü girin"
        ).strip().upper()
        
        st.divider()
        
        # Tarih aralığı
        st.subheader("📅 Tarih Aralığı")
        col1, col2 = st.columns(2)
        baslangic = col1.number_input("Başlangıç", 2010, 2026, 2019)
        bitis = col2.number_input("Bitiş", 2010, 2026, 2026)
        
        st.divider()
        
        # Analiz butonu
        analiz = st.button(
            "📊 Analiz Et", 
            type="primary", 
            use_container_width=True,
            disabled=not ticker
        )
        
        if not ticker:
            st.warning("⚠️ Lütfen bir ticker girin")
    
    # Ana alan
    if analiz:
        if not ticker:
            st.error("❌ Lütfen bir ticker girin!")
            return
        
        # Tarihleri bir yıl önceden başlat (ocak ayını dahil etmek için)
        baslangic_str = f"{baslangic-1}-12-01"
        bitis_str = f"{bitis}-12-31"
        
        with st.spinner(f"📊 {ticker} verileri çekiliyor..."):
            veri = get_data(ticker, baslangic_str, bitis_str)
            fiyat_pivot, currency_symbol = get_price_data(ticker, baslangic_str, bitis_str)
        
        if veri is not None and not veri.empty:
            # Sadece seçilen yılları göster
            veri = veri[veri.index >= baslangic]
            if fiyat_pivot is not None:
                fiyat_pivot = fiyat_pivot[fiyat_pivot.index >= baslangic]
            
            st.success(f"✅ {ticker} için {len(veri)} yıllık veri yüklendi ({baslangic}-{bitis})")
            
            # Güncel fiyat bilgisi
            current_price, curr_symbol, price_change = get_current_price(ticker)
            
            if current_price and curr_symbol:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.info(f"📍 **Şu Anki Fiyat:** {curr_symbol}{current_price:,.2f}")
                with col2:
                    if price_change >= 0:
                        st.success(f"📈 Dünden beri: +{price_change:.2f}%")
                    else:
                        st.error(f"📉 Dünden beri: {price_change:.2f}%")
            
            st.divider()
            
            # Metrikler
            aylik_ort = veri.mean()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("En İyi Ay", aylik_ort.idxmax(), f"+{aylik_ort.max():.1f}%")
                st.caption("Genelde en çok yükseldiği ay")
            
            with col2:
                st.metric("En Kötü Ay", aylik_ort.idxmin(), f"{aylik_ort.min():.1f}%")
                st.caption("Genelde en çok düştüğü ay")
            
            with col3:
                pozitif = (aylik_ort > 0).sum()
                st.metric("Yükseliş Ayları", f"{pozitif}/12")
                st.caption(f"{pozitif} ay yükseliş, {12-pozitif} ay düşüş")
            
            st.divider()
            
            # Isı haritası - Sadece 2 renk: yeşil ve kırmızı
            st.subheader("📅 Aylık Performans Tablosu")
            st.caption("🟢 Yeşil = Yükseliş | 🔴 Kırmızı = Düşüş")
            
            # Fiyat ve yüzde bilgisini birleştir
            if fiyat_pivot is not None and currency_symbol:
                # Text için hem yüzde hem fiyat
                text_labels = []
                for i, yil in enumerate(veri.index):
                    row_labels = []
                    for j, ay in enumerate(veri.columns):
                        yuzde = veri.iloc[i, j]
                        
                        # Fiyat bilgisi varsa ekle
                        if yil in fiyat_pivot.index and ay in fiyat_pivot.columns:
                            fiyat = fiyat_pivot.loc[yil, ay]
                            if pd.notna(yuzde) and pd.notna(fiyat):
                                # + veya - işareti ekle
                                isaret = "+" if yuzde >= 0 else ""
                                row_labels.append(f"{isaret}{yuzde:.1f}%<br>{currency_symbol}{fiyat:.2f}")
                            elif pd.notna(yuzde):
                                isaret = "+" if yuzde >= 0 else ""
                                row_labels.append(f"{isaret}{yuzde:.1f}%")
                            else:
                                row_labels.append("")
                        else:
                            if pd.notna(yuzde):
                                isaret = "+" if yuzde >= 0 else ""
                                row_labels.append(f"{isaret}{yuzde:.1f}%")
                            else:
                                row_labels.append("")
                    text_labels.append(row_labels)
                
                # Sadece 2 renk: kırmızı ve yeşil
                fig = go.Figure(data=go.Heatmap(
                    z=veri.values,
                    x=veri.columns,
                    y=veri.index,
                    colorscale=[[0, '#ff4444'], [0.5, '#ffffff'], [1, '#44ff44']],  # Kırmızı -> Beyaz -> Yeşil
                    zmid=0,
                    text=text_labels,
                    texttemplate='%{text}',
                    colorbar=dict(title="%")
                ))
            else:
                # Sadece yüzde
                # Text etiketleri oluştur (+ işareti ile)
                text_labels = []
                for i in range(len(veri)):
                    row_labels = []
                    for j in range(len(veri.columns)):
                        val = veri.iloc[i, j]
                        if pd.notna(val):
                            isaret = "+" if val >= 0 else ""
                            row_labels.append(f"{isaret}{val:.1f}%")
                        else:
                            row_labels.append("")
                    text_labels.append(row_labels)
                
                fig = go.Figure(data=go.Heatmap(
                    z=veri.values,
                    x=veri.columns,
                    y=veri.index,
                    colorscale=[[0, '#ff4444'], [0.5, '#ffffff'], [1, '#44ff44']],  # Kırmızı -> Beyaz -> Yeşil
                    zmid=0,
                    text=text_labels,
                    texttemplate='%{text}',
                    colorbar=dict(title="%")
                ))
            
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # Bar chart
            st.subheader("📊 Hangi Aylarda Ortalama Ne Kadar Değişiyor?")
            
            fig2 = go.Figure()
            renkler = ['green' if x > 0 else 'red' for x in aylik_ort.values]
            
            fig2.add_trace(go.Bar(
                x=aylik_ort.index,
                y=aylik_ort.values,
                marker_color=renkler,
                text=[f"{x:+.1f}%" for x in aylik_ort.values],
                textposition='outside'
            ))
            
            fig2.update_layout(height=300, showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig2, use_container_width=True)
            
            st.divider()
            
            # Öneriler
            st.subheader("💡 Ne Yapmalıyım?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.success("**✅ ALIM ÖNERİSİ (Ucuz Aylar)**")
                st.write("Bu aylarda genelde düşüş var, almak için iyi:")
                en_kotu = aylik_ort.nsmallest(3)
                for i, (ay, val) in enumerate(en_kotu.items(), 1):
                    st.write(f"{i}. **{ay}** → Ortalama {val:.1f}%")
            
            with col2:
                st.error("**💰 SATIM ÖNERİSİ (Pahalı Aylar)**")
                st.write("Bu aylarda genelde yükseliş var, satmak için iyi:")
                en_iyi = aylik_ort.nlargest(3)
                for i, (ay, val) in enumerate(en_iyi.items(), 1):
                    st.write(f"{i}. **{ay}** → Ortalama +{val:.1f}%")
            
            st.divider()
            
            # Başarı tablosu - Düşüş sütunu eklendi
            st.subheader("📋 Detaylı İstatistik")
            st.caption("Her ay kaç kere yükselmiş/düşmüş?")
            
            basari = []
            for ay in veri.columns:
                poz = (veri[ay] > 0).sum()
                neg = (veri[ay] < 0).sum()
                top = veri[ay].notna().sum()
                if top > 0:
                    basari.append({
                        'Ay': ay,
                        'Yükseliş': f"{int(poz)} kez",
                        'Düşüş': f"{int(neg)} kez",
                        'Toplam': f"{int(top)} yıl",
                        'Başarı': f"%{(poz/top*100):.0f}"
                    })
            
            basari_df = pd.DataFrame(basari)
            st.dataframe(basari_df, use_container_width=True, hide_index=True)
            
            st.caption("Örnek: Nisan 6 kez yükselmiş, 2 kez düşmüş, toplam 8 yıl var → %75 başarı oranı")
            
            st.divider()
            
            st.warning("⚠️ **Önemli:** Geçmiş performans gelecek garantisi değildir. Sadece referans amaçlıdır.")
        
        else:
            st.error(f"❌ '{ticker}' için veri çekilemedi! Ticker sembolünü kontrol edin.")
            st.info("""
            **Ticker bulunamadı mı?**
            - Yahoo Finance'de ticker'ı arayın: https://finance.yahoo.com
            - Doğru formatı kullanın (Örn: AAPL, BTC-USD, ^GSPC)
            - Türk hisseleri için .IS ekleyin (Örn: GARAN.IS)
            """)
    
    else:
        st.info("👈 Sol menüden bir ticker girin ve 'Analiz Et' butonuna tıklayın")
        
        st.markdown("""
        ### 🤔 Nasıl Kullanılır?
        
        1. **Sol menüden** bir ticker girin (Örn: AAPL, BTC-USD)
        2. **Tarih aralığını** seçin
        3. **Analiz Et** butonuna tıklayın
        
        ### 💡 Ticker Nasıl Bulunur?
        
        1. **Yahoo Finance**'e gidin: https://finance.yahoo.com
        2. Aramak istediğiniz şirketi/varlığı arayın
        3. Ticker sembolünü kopyalayın
                    
        ### 📊 Ne Öğreneceksiniz?
        
        - **Güncel fiyat** ve değişim
        - **Aylık performans tablosu** (hem yüzde hem fiyat)
        - Hangi aylarda genelde yükseliş/düşüş oluyor
        - En iyi alım/satım zamanları
        - Geçmiş performans istatistikleri
        
        **Basit mantık:** Düşükten al, yüksekten sat 📈
        """)

if __name__ == "__main__":
    main()