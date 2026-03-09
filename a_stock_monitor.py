#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股集合竞价监控脚本 - 云端版
适用于GitHub Actions
"""

import os
import sys
import datetime
import time
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
    # 剔除ST股票
    df_clean = df_clean[~df_clean['名称'].str.contains('ST|退', na=False)]
    # 涨跌幅筛选
    if '涨跌幅' in df_clean.columns:
        df_clean = df_clean[(df_clean['涨跌幅'] > 2) & (df_clean['涨跌幅'] < 10)]
    # 成交量筛选
    if '成交量' in df_clean.columns:
        df_clean = df_clean[df_clean['成交量'] > 0]
    # 换手率筛选
    if '换手率' in df_clean.columns:
        df_clean['换手率'] = pd.to_numeric(df_clean['换手率'], errors='coerce')
        df_clean = df_clean[df_clean['换手率'] > 0.1]
    df_clean = df_clean.sort_values('涨跌幅', ascending=False)
    df_top = df_clean.head(10)
    results = []
    for idx, row in df_top.iterrows():
        results.append({
            '代码
