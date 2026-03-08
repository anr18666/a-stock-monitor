#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股集合竞价监控脚本 - 云端版
适用于GitHub Actions
"""

import os
import sys
import datetime
import json
import pandas as pd
import numpy as np
import requests

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_stock_data():
    import akshare as ak
    log("正在获取A股行情数据...")
    max_retries = 3
    retry_delay = 3
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_spot_em()
            log(f"成功获取 {len(df)} 条股票数据")
            return df
        except Exception as e:
            log(f"获取数据失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
    return None

def get_sector_data():
    import akshare as ak
    log("正在获取板块行情数据...")
    max_retries = 3
    retry_delay = 3
    for attempt in range(max_retries):
        try:
            df = ak.stock_board_industry_name_em()
            log(f"成功获取 {len(df)} 个板块数据")
            return df
        except Exception as e:
            log(f"获取板块数据失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
    return None

def filter_volume_stocks(df):
    if df is None or df.empty:
        return []
    log("正在筛选备量个股...")
    df_clean = df.copy()
    numeric_cols = ['最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '振幅', '换手率', '市盈率-动态', '市净率']
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    df_clean = df_clean[~df_clean['名称'].str.contains('ST|退', na=False)]
    if '涨跌幅' in df_clean.columns:
        df_clean = df_clean[(df_clean['涨跌幅'] > 2) & (df_clean['涨跌幅'] < 10)]
    if '成交量' in df_clean.columns:
        df_clean = df_clean[df_clean['成交量'] > 0]
    if '换手率' in df_clean.columns:
        df_clean['换手率'] = pd.to_numeric(df_clean['换手率'], errors='coerce')
        df_clean = df_clean[df_clean['换手率'] > 0.1]
    df_clean = df_clean.sort_values('涨跌幅', ascending=False)
    df_top = df_clean.head(10)
    results = []
    for idx, row in df_top.iterrows():
        results.append({
            '代码': row.get('代码', ''),
            '名称': row.get('名称', ''),
            '最新价': float(row.get('最新价', 0)) if pd.notna(row.get('最新价')) else 0,
            '涨跌幅': float(row.get('涨跌幅', 0)) if pd.notna(row.get('涨跌幅')) else 0,
            '成交量': int(row.get('成交量', 0)) if pd.notna(row.get('成交量')) else 0,
            '成交额': int(row.get('成交额', 0)) if pd.notna(row.get('成交额')) else 0,
        })
    log(f"筛选出 {len(results)} 只备量个股")
    return results

def get_top_sectors(sector_df, top_n=5):
    if sector_df is None or sector_df.empty:
        return []
    log("正在分析上涨板块...")
    sector_df = sector_df.copy()
    sector_df['涨跌幅'] = pd.to_numeric(sector_df['涨跌幅'], errors='coerce')
    sector_up = sector_df[sector_df['涨跌幅'] > 0.5].copy()
    sector_up = sector_up.sort_values('涨跌幅', ascending=False)
    sector_top = sector_up.head(top_n)
    results = []
    for idx, row in sector_top.iterrows():
        results.append({
            '板块名称': row.get('板块名称', ''),
            '涨跌幅': float(row.get('涨跌幅', 0)) if pd.notna(row.get('涨跌幅')) else 0,
        })
    log(f"找到 {len(results)} 个上涨板块")
    return results

def send_notification(title, content, push_key, push_type='bark'):
    try:
        if push_type == 'bark':
            url = f"https://api.day.app/{push_key}/{title}/{content}"
            response = requests.get(url, timeout=10)
            log(f"Bark通知发送结果: {response.status_code}")
            return response.status_code == 200
        elif push_type == 'serverchan':
            url = f"https://www.serverchan.com/api/v1/send"
            data = {"text": title, "desp": content}
            response = requests.post(url, json=data, timeout=10)
            log(f"ServerChan通知发送结果: {response.status_code}")
            return response.status_code == 200
        return False
    except Exception as e:
        log(f"通知发送失败: {e}")
        return False

def format_message(sectors, stocks):
    msg = f"📈 A股9:25 集合竞价监控\n"
    msg += f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    if sectors:
        msg += "🔥 上涨板块 TOP 5:\n"
        for i, s in enumerate(sectors[:5], 1):
            msg += f"  {i}. {s['板块名称']} +{s['涨跌幅']:.2f}%\n"
        msg += "\n"
    if stocks:
        msg += "📊 备量个股 TOP 10:\n"
        for i, s in enumerate(stocks[:10], 1):
            msg += f"  {i}. {s['名称']} {s['最新价']:.2f} (+{s['涨跌幅']:.2f}%)\n"
    else:
        msg += "⚠️ 暂无备量个股数据\n"
    return msg

def main():
    log("A股集合竞价监控程序启动")
    push_key = os.environ.get('PUSH_KEY', '')
    push_type = os.environ.get('PUSH_TYPE', 'bark')
    log(f"推送类型: {push_type}")
    stock_df = get sector_df = get_sector_data()
_stock_data()
       volume_stocks = filter_volume_stocks(stock_df)
    top_sectors = get_top_sectors(sector_df)
    print("\n" + "="*60)
    print("【A股9:25 集合竞价监控汇总】")
    print("="*60)
    if top_sectors:
        print("\n🔥 上涨板块 TOP 5:")
        for i, s in enumerate(top_sectors[:5], 1):
            print(f"  {i}. {s['板块名称']} +{s['涨跌幅']:.2f}%")
    if volume_stocks:
        print("\n📊 备量个股 TOP 10:")
        for i, s in enumerate(volume_stocks[:10], 1):
            print(f"  {i}. {s['名称']} {s['最新价']:.2f} (+{s['涨跌幅']:.2f}%)")
    else:
        print("\n⚠️ 暂无备量个股数据")
    print("\n" + "="*60 + "\n")
    if push_key:
        title = "A股监控 9:25"
        content = format_message(top_sectors, volume_stocks)
        send_notification(title, content, push_key, push_type)
    log("监控完成!")

if __name__ == "__main__":
    main()
