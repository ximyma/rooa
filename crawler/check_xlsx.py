# -*- coding: utf-8 -*-
import pandas as pd
df = pd.read_excel(r'C:\Users\Administrator\Desktop\ooa\crawler\url_2.xlsx')
print('Columns:', df.columns.tolist())
print('\n---First5---')
print(df.head())