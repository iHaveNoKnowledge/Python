# **TABLES FOR SMCO ADDRESS ENUM DROPDOWNS**

1. V_DISTRICT_SEARCH
2. V_SUBDISTRICT_SEARCH
3. V_PROVINCE_SEARCH
4. [V_REGION_MASTER]
	สำหรับหา FILTER หา FORMAT ของ ADDRESS ซึ่งในตารางนี้มันจะมี ID   

---

ลองเอาไปเช็คกับ response ของ endpoint /getCountryInfomation.htm จาก smco ดู ได้จากตอนกด dropdown ในหน้าสร้าง new customer

> ตัวอย่าง JSON จาก TABLE V_DISTRICT_SEARCH

```
[
  {
    "DISTRICT_ID": 358,
    "DISTRICT_CODE": "009610",
    "DISTRICT_NAMEEN": "Su-ngai Kolok",
    "DISTRICT_NAMETH": "สุไหงโกลก",
    "COUNTRY_ID": 1,
    "COUNTRY_CODE": "1",
    "COUNTRY_NAMEEN": "Thailand",
    "COUNTRY_NAMETH": "ไทย",
    "REGION_ID": 8,
    "REGION_CODE": "80",
    "REGION_NAMEEN": "South",
    "REGION_NAMETH": "ภาคใต้",
    "PROVINCE_ID": 67,
    "PROVINCE_CODE": "96",
    "PROVINCE_NAMEEN": "Narathiwat",
    "PROVINCE_NAMETH": "นราธิวาส",
    "ACTIVE_FLAG": true,
    "DELETE_FLAG": false,
    "CREATED_BY_ID": 1,
    "CREATED_BY_NAMEEN": "9999999 - AR Soft",
    "CREATED_BY_NAMETH": "9999999 - AR Soft",
    "CREATED_DATE": "2019-12-06T19:06:01.123"
  }
]
```

```
[
  {
    "ROW_NO": "167358958958",
    "COUNTRY_ID": 1,
    "COUNTRY_CODE": "1",
    "COUNTRY_NAME_EN": "Thailand",
    "COUNTRY_NAME_TH": "ไทย",
    "PROVINCE_ID": 67,
    "PROVINCE_CODE": "96",
    "PROVINCE_NAME_EN": "Narathiwat",
    "PROVINCE_NAME_TH": "นราธิวาส",
    "BKK_FLAG": false,
    "DISTRICT_ID": 358,
    "DISTRICT_CODE": "009610",
    "DISTRICT_NAME_EN": "Su-ngai Kolok",
    "DISTRICT_NAME_TH": "สุไหงโกลก",
    "SUBDISTRICT_ID": 958,
    "SUBDISTRICT_CODE": "961002",
    "SUBDISTRICT_NAME_EN": "Pa Semat",
    "SUBDISTRICT_NAME_TH": "ป่าเสมัส",
    "ZIPCODE_ID": 958,
    "ZIPCODE": 96120
  },
  {
    "ROW_NO": "16735819771977",
    "COUNTRY_ID": 1,
    "COUNTRY_CODE": "1",
    "COUNTRY_NAME_EN": "Thailand",
    "COUNTRY_NAME_TH": "ไทย",
    "PROVINCE_ID": 67,
    "PROVINCE_CODE": "96",
    "PROVINCE_NAME_EN": "Narathiwat",
    "PROVINCE_NAME_TH": "นราธิวาส",
    "BKK_FLAG": false,
    "DISTRICT_ID": 358,
    "DISTRICT_CODE": "009610",
    "DISTRICT_NAME_EN": "Su-ngai Kolok",
    "DISTRICT_NAME_TH": "สุไหงโกลก",
    "SUBDISTRICT_ID": 1977,
    "SUBDISTRICT_CODE": "961004",
    "SUBDISTRICT_NAME_EN": "Puyo",
    "SUBDISTRICT_NAME_TH": "ปูโยะ",
    "ZIPCODE_ID": 1977,
    "ZIPCODE": 96120
  },
  {
    "ROW_NO": "16735863866386",
    "COUNTRY_ID": 1,
    "COUNTRY_CODE": "1",
    "COUNTRY_NAME_EN": "Thailand",
    "COUNTRY_NAME_TH": "ไทย",
    "PROVINCE_ID": 67,
    "PROVINCE_CODE": "96",
    "PROVINCE_NAME_EN": "Narathiwat",
    "PROVINCE_NAME_TH": "นราธิวาส",
    "BKK_FLAG": false,
    "DISTRICT_ID": 358,
    "DISTRICT_CODE": "009610",
    "DISTRICT_NAME_EN": "Su-ngai Kolok",
    "DISTRICT_NAME_TH": "สุไหงโกลก",
    "SUBDISTRICT_ID": 6386,
    "SUBDISTRICT_CODE": "961001",
    "SUBDISTRICT_NAME_EN": "Su-Ngai Ko-Lok",
    "SUBDISTRICT_NAME_TH": "สุไหงโก-ลก",
    "ZIPCODE_ID": 6386,
    "ZIPCODE": 96120
  },
  {
    "ROW_NO": "16735867286728",
    "COUNTRY_ID": 1,
    "COUNTRY_CODE": "1",
    "COUNTRY_NAME_EN": "Thailand",
    "COUNTRY_NAME_TH": "ไทย",
    "PROVINCE_ID": 67,
    "PROVINCE_CODE": "96",
    "PROVINCE_NAME_EN": "Narathiwat",
    "PROVINCE_NAME_TH": "นราธิวาส",
    "BKK_FLAG": false,
    "DISTRICT_ID": 358,
    "DISTRICT_CODE": "009610",
    "DISTRICT_NAME_EN": "Su-ngai Kolok",
    "DISTRICT_NAME_TH": "สุไหงโกลก",
    "SUBDISTRICT_ID": 6728,
    "SUBDISTRICT_CODE": "961003",
    "SUBDISTRICT_NAME_EN": "Mu No",
    "SUBDISTRICT_NAME_TH": "มูโนะ",
    "ZIPCODE_ID": 6728,
    "ZIPCODE": 96120
  }
]
```



> ตัวอย่าง JSON จาก response ของ endpoint /getCountryInfomation.htm

```
[{
	"districtCode": "009610",
	"districtNameTh": "สุไหงโกลก",
	"districtNameEn": "Su-ngai Kolok",
	"provinceId": 67,
	"countryId": 1,
	"regionId": 8,
	"active": true,
	"delete": false,
	"activeFlag": false,
	"deleteFlag": false,
	"footprint": {
		"createdDate": "Dec 6, 2019 7:06:01 PM",
		"createdBy": "1",
		"empLoginCreate": {
			"userId": 1,
			"empId": 2661,
			"nameTh": "9999999 - AR Soft",
			"nameEn": "9999999 - AR Soft",
			"picture": "/1573114942592.png",
			"deptId": 12,
			"department": "สารสนเทศ",
			"userActiveFlag": "Y",
			"userDeleteFlag": "N",
			"footprint": {}
		}
	},
	"id": 358
}]
```
