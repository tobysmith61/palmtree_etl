#DMS_CUSTOMER_FEED_RAW_MAPPINGS
import pandas as pd

df = pd.read_excel(
    "files/DMS_Customer_Feed_Raw_Mappings.ods",
    engine="odf",
    sheet_name='DMS_CUSTOMER_FEED_RAW_MAPPINGS'
)

print(df)

# Goal at stage 1 is to read from workbook and store as canonicalised only in postgres
