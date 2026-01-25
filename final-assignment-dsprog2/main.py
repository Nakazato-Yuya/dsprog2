import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import os
import time
import platform
import requests
import io

# --- フォント設定 ---
system_name = platform.system()
if system_name == 'Darwin': # Mac
    plt.rcParams['font.family'] = 'Hiragino Sans'
elif system_name == 'Windows': # Windows
    plt.rcParams['font.family'] = 'MS Gothic'
else:
    plt.rcParams['font.family'] = 'sans-serif'

class RegionScraper:
    def __init__(self):
        self.url = "https://ja.wikipedia.org/wiki/%E9%83%BD%E9%81%93%E5%BA%9C%E7%9C%8C"
        # バックアップデータ（万が一のため）
        self.backup_data = {
            "北海道": "北海道", "青森": "東北", "岩手": "東北", "宮城": "東北", "秋田": "東北", "山形": "東北", "福島": "東北",
            "茨城": "関東", "栃木": "関東", "群馬": "関東", "埼玉": "関東", "千葉": "関東", "東京": "関東", "神奈川": "関東",
            "新潟": "中部", "富山": "中部", "石川": "中部", "福井": "中部", "山梨": "中部", "長野": "中部", "岐阜": "中部", "静岡": "中部", "愛知": "中部",
            "三重": "近畿", "滋賀": "近畿", "京都": "近畿", "大阪": "近畿", "兵庫": "近畿", "奈良": "近畿", "和歌山": "近畿",
            "鳥取": "中国", "島根": "中国", "岡山": "中国", "広島": "中国", "山口": "中国",
            "徳島": "四国", "香川": "四国", "愛媛": "四国", "高知": "四国",
            "福岡": "九州", "佐賀": "九州", "長崎": "九州", "熊本": "九州", "大分": "九州", "宮崎": "九州", "鹿児島": "九州", "沖縄": "九州"
        }

    def scrape(self):
        print(f"Webサイトからデータを取得中...: {self.url}")
        time.sleep(2) 
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(self.url, headers=headers)
            response.raise_for_status()
            
            dfs = pd.read_html(io.StringIO(response.text))
            
            target_df = None
            pref_col_idx = -1
            region_col_idx = -1

            for df in dfs:
                df_str = df.astype(str)
                if len(df) < 40: continue

                for i in range(len(df.columns)):
                    col_values = df_str.iloc[:, i].tolist()
                    if any("北海道" in v for v in col_values):
                        pref_col_idx = i
                    if any("東北" in v for v in col_values) and any("関東" in v for v in col_values):
                        region_col_idx = i
                
                if pref_col_idx != -1 and region_col_idx != -1:
                    target_df = df
                    break

            if target_df is not None:
                result = target_df.iloc[:, [pref_col_idx, region_col_idx]].copy()
                result.columns = ['prefecture', 'region']
                # 余計な文字を削除
                result['prefecture'] = result['prefecture'].astype(str).str.replace(r'\[.*?\]', '', regex=True)
                result = result[result['prefecture'].str.contains("都|道|府|県")]
                print(" >> スクレイピング成功！ Webデータを使用します。")
                return result
            
            raise Exception("テーブルが見つかりません")
            
        except Exception as e:
            print(f"警告: スクレイピング失敗 ({e})。バックアップを使用します。")
            # バックアップデータ使用時は「県」などを抜いたキーで作成
            return pd.DataFrame(list(self.backup_data.items()), columns=['prefecture', 'region'])

class DataManager:
    def __init__(self, db_name="final_analysis.db"):
        self.db_name = db_name

    def clean_name(self, name):
        """徹底的にゴミを取り除く"""
        if pd.isna(name): return ""
        # 全角スペース、半角スペース、改行を削除
        name = str(name).replace("　", "").replace(" ", "").replace("\n", "").strip()
        # 都・道・府・県 も削除して「名寄せ」しやすくする
        name = name.replace("都", "").replace("道", "").replace("府", "").replace("県", "")
        return name

    def process_excel_files(self, land_file, tax_file, df_region):
        conn = sqlite3.connect(self.db_name)
        print("\nExcelファイルの読み込みとDB保存を開始します...")

        # 1. 地価データ
        try:
            df_land = pd.read_excel(land_file, sheet_name='22', header=2)
            df_land = df_land.iloc[:, [1, 22]]
            df_land.columns = ['prefecture', 'land_price']
            # ここでclean_nameを使って「県」などを削除した純粋な名前だけにする
            df_land['prefecture'] = df_land['prefecture'].apply(self.clean_name)
            df_land = df_land[df_land['prefecture'] != '全国合計']
            df_land['land_price'] = pd.to_numeric(df_land['land_price'], errors='coerce')
            df_land.dropna().to_sql('land_prices', conn, if_exists='replace', index=False)
            print(f" >> 地価データ保存完了")
        except Exception as e:
            print(f"【エラー】地価ファイル: {e}")

        # 2. 税収データ
        try:
            xls = pd.ExcelFile(tax_file)
            target_sheet = next((s for s in xls.sheet_names if 'その３' in s or 'Part3' in s), None)
            if target_sheet:
                df_tax = pd.read_excel(tax_file, sheet_name=target_sheet, header=None)
                df_tax = df_tax.iloc[9:, [1, 8]]
                df_tax.columns = ['prefecture', 'tax_revenue']
                df_tax['prefecture'] = df_tax['prefecture'].apply(self.clean_name)
                df_tax = df_tax[~df_tax['prefecture'].isin(['局引受分', '計', 'nan', ''])]
                df_tax['tax_revenue'] = pd.to_numeric(df_tax['tax_revenue'], errors='coerce')
                df_tax.dropna().to_sql('tax_revenue', conn, if_exists='replace', index=False)
                print(f" >> 税収データ保存完了")
            else:
                print("【エラー】税収データシートなし")
        except Exception as e:
            print(f"【エラー】税収ファイル: {e}")

        # 3. 地方データ
        if df_region is not None:
            # Webデータも同じ基準でクリーニングする（これが重要！）
            df_region['join_key'] = df_region['prefecture'].apply(self.clean_name)
            df_region.to_sql('regions', conn, if_exists='replace', index=False)
            print(" >> 地方データ保存完了")
        
        conn.close()

class Analyzer:
    def __init__(self, db_name="final_analysis.db"):
        self.db_name = db_name
        # 最終手段としてのバックアップマップ
        self.region_map = {
            "北海道": "北海道", "青森": "東北", "岩手": "東北", "宮城": "東北", "秋田": "東北", "山形": "東北", "福島": "東北",
            "茨城": "関東", "栃木": "関東", "群馬": "関東", "埼玉": "関東", "千葉": "関東", "東京": "関東", "神奈川": "関東",
            "新潟": "中部", "富山": "中部", "石川": "中部", "福井": "中部", "山梨": "中部", "長野": "中部", "岐阜": "中部", "静岡": "中部", "愛知": "中部",
            "三重": "近畿", "滋賀": "近畿", "京都": "近畿", "大阪": "近畿", "兵庫": "近畿", "奈良": "近畿", "和歌山": "近畿",
            "鳥取": "中国", "島根": "中国", "岡山": "中国", "広島": "中国", "山口": "中国",
            "徳島": "四国", "香川": "四国", "愛媛": "四国", "高知": "四国",
            "福岡": "九州", "佐賀": "九州", "長崎": "九州", "熊本": "九州", "大分": "九州", "宮崎": "九州", "鹿児島": "九州", "沖縄": "九州"
        }

    def analyze(self, target_region=None):
        conn = sqlite3.connect(self.db_name)
        
        # 結合クエリ（join_keyを使用）
        query = """
        SELECT 
            T1.prefecture, 
            T1.land_price, 
            T2.tax_revenue,
            T3.region
        FROM land_prices AS T1
        JOIN tax_revenue AS T2 ON T1.prefecture = T2.prefecture
        LEFT JOIN regions AS T3 ON T1.prefecture = T3.join_key
        """

        try:
            df = pd.read_sql(query, conn)
        except Exception as e:
            print(f"DB Error: {e}")
            conn.close()
            return

        conn.close()

        # 【重要】もしDB結合でregionが取れていなくても、ここで強制的に埋める
        if df['region'].isna().all() or df['region'].isna().sum() > 20:
            print("【補正】Webデータの結合が不十分なため、内蔵データで補完します。")
            df['region'] = df['prefecture'].map(self.region_map)

        # 動的フィルタリング
        title_text = '【全国】都道府県の経済力(税収)と地価の相関'
        if target_region and target_region != "すべて":
            # ユーザー入力を部分一致で検索
            filtered_df = df[df['region'].astype(str).str.contains(target_region, na=False)]
            
            if not filtered_df.empty:
                df = filtered_df
                title_text = f'【{target_region}】経済力(税収)と地価の相関'
            else:
                print(f"\n【注意】'{target_region}' のデータが見つかりませんでした。")
                print("（入力例：関東、近畿、九州）")
                print("※全国データを表示します。")

        # 分析結果
        print(f"\n--- 分析結果 ({title_text}) ---")
        print(f"分析対象数: {len(df)}")
        if len(df) > 1:
            print(f"相関係数: {df['land_price'].corr(df['tax_revenue']):.4f}")

        # グラフ描画
        plt.figure(figsize=(10, 6))
        
        df['region'] = df['region'].fillna('その他')
        regions = df['region'].unique()
        
        # 色分けプロット
        for r in regions:
            subset = df[df['region'] == r]
            plt.scatter(subset['tax_revenue'], subset['land_price'], label=r, s=100, alpha=0.7, edgecolors='white')

        # ラベル表示
        for i, row in df.iterrows():
            # データ数が少ない(絞り込み時)は全ラベル表示
            if len(df) < 15 or row['tax_revenue'] > df['tax_revenue'].quantile(0.85) or row['land_price'] > df['land_price'].quantile(0.85):
                plt.text(row['tax_revenue'], row['land_price'], row['prefecture'], fontsize=9, ha='left')

        plt.title(title_text)
        plt.xlabel('国税収納済額 (百万円)')
        plt.ylabel('平均地価 (円/㎡)')
        plt.legend(title="地方", bbox_to_anchor=(1.02, 1), loc='upper left')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        
        # 保存
        filename = "result_graph.png"
        plt.savefig(filename)
        print(f"\n★グラフを保存しました！: {filename}")
        print("左側のファイル一覧から 'result_graph.png' をクリックして結果を確認してください。")

if __name__ == "__main__":
    scraper = RegionScraper()
    df_region = scraper.scrape()
    
    file_land = "r05_xlsx_allfile2.xlsx"
    file_tax = "r05_1001.xlsx"
    
    if os.path.exists(file_land) and os.path.exists(file_tax):
        manager = DataManager()
        manager.process_excel_files(file_land, file_tax, df_region)
        
        print("\n分析したい地域を選んでください（例: 関東, 近畿, 九州, 東北）")
        print("何も入力せずにEnterを押すと「全国」を分析します。")
        user_input = input("地域名を入力 > ").strip()
        target = user_input if user_input else "すべて"
        
        analyzer = Analyzer()
        analyzer.analyze(target)
    else:
        print("エラー: ファイルが見つかりません。")