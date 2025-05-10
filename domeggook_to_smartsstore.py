import http.client
import bcrypt
import pybase64
import urllib.parse
import json
import time
import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict
import mimetypes
import uuid

@dataclass
class Product:
    title: str                  #제목
    price: str                  #가격
    inventory: str              #재고
    representativeImage: str    #대표이미지
    optionalImages: str         #추가이미지
    baseFee: int                #기본배송비
    secondExtraFee: int     #제주추가배송비
    thirdExtraFee: int      #도서산간추가배송비
    originAreaCode: str     #원산지정보
    manufacturerName: str   #제조사
    selectOpt: Dict[str, str]          #옵션
    

# 필요한 필드 추가

# 설정 값 (clientId, clientSecret 등)
client_id = "5XJumV8jd3c2dbG9oF98X1"
client_secret = "$2a$04$Oi1tLN44O4mhRHUoaJzrVO"

def generate_client_secret_sign(client_id, client_secret):
    """
    주어진 client_id와 client_secret을 이용하여 client_secret_sign을 생성합니다.
    """
    # 현재 Unix 시간 (밀리초 단위)
    timestamp = int(time.time() * 1000)

    # client_id와 timestamp로 password 생성
    password = f"{client_id}_{timestamp}"

    # bcrypt 해싱
    hashed = bcrypt.hashpw(password.encode('utf-8'), client_secret.encode('utf-8'))

    # base64 인코딩
    client_secret_sign = pybase64.standard_b64encode(hashed).decode('utf-8')
    
    return timestamp, client_secret_sign

def get_access_token(client_id, client_secret):
    """
    API에 요청을 보내어 access_token을 얻어옵니다.
    """
    timestamp, client_secret_sign = generate_client_secret_sign(client_id, client_secret)

    # 토큰 요청 파라미터 설정
    params = {
        'client_id': client_id,
        'timestamp': str(timestamp),
        'grant_type': 'client_credentials',
        'client_secret_sign': client_secret_sign,
        'type': 'SELF'
    }

    payload = urllib.parse.urlencode(params)

    # 요청 헤더 설정
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    # HTTP 요청 보내기
    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    conn.request("POST", "/external/v1/oauth2/token", payload, headers)
    res = conn.getresponse()
    
    # 응답에서 토큰 추출
    data = res.read()
    token = json.loads(data.decode("utf-8"))["access_token"]

    return token

def domeggook_search_product() -> Product:

    # API URL
    url = "https://domeggook.com/ssl/api"

    params = {
        'ver': '4.5',
        'mode': 'getItemView',
        'aid': '5770d1b96006f2b3c91631b6e8d4cadc',
        'om': 'xml',
        'no': '19192044'  # 조회할 상품 번호
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        root = ET.fromstring(response.text)
        # items = root.findall('./list/item')
        # if not items:
        #     print("상품이 없습니다.")
        # else:
        #     for item in items:
        title = "자동차 차량용 고급 목쿠션"#root.findtext('.//title')                              #상풍명
        price = root.findtext('.//price//dome')                              #금액
        inventory =  root.findtext('.//qty/inventory')                     #재고
        representativeImage = root.findtext('.//thumb/original')             #썸네일url
        optionalImages = root.findtext('.//thumb/original')                  #옵션이미지url
        baseFee = root.findtext('.//deli//dome//fee')                              #기본배송비
        secondExtraFee = root.findtext('.//jeju')                      #제주추가배송비
        thirdExtraFee = root.findtext('.//islands')                    #도서산간 추가 배송비
        originAreaCode = map_origin_code(root.findtext('.//country'))#원산지
        manufacturerName = root.findtext('.//detail//manufacturer') #제조사
        selectOpt = map_option_code(root.findtext('.//selectOpt'))     #옵션
    


        return Product(
            title=title,
            price=price,
            inventory = inventory,
            representativeImage = representativeImage,
            optionalImages = optionalImages,
            baseFee = baseFee,
            secondExtraFee = secondExtraFee,
            thirdExtraFee = thirdExtraFee,
            originAreaCode = originAreaCode,
            manufacturerName = manufacturerName,
            selectOpt = selectOpt
        )
    else:
        print("HTTP 요청 실패:", response.status_code)
        return None

def map_origin_code(text: str) -> str:
    origin_map = {
        "국산": "00",
        "원양산": "01",
        "수입산": "02",
        "기타-상세 설명에 표시": "03",
        "기타-직접 입력": "04",
        "원산지 표기 의무 대상 아님": "05"
    }

    for key in origin_map:
        if key in text:
            return origin_map[key]
    
    return "기타 없음"  # 매칭되지 않으면 기본값

def map_option_code(text: str) -> str:
    parsed = json.loads(text)
    # 예시: 첫 번째 set의 name 출력
    group_name = parsed['set'][0]['name']
    option_values = parsed['set'][0]['opts']
    # option_values_joined = ','.join(option_values)

    # 결과 구조
    result = {
        "groupName": group_name,
        "name": option_values
    }

    return json.dumps(result, ensure_ascii=False)

def fetch_product_data(token):
    """
    access_token을 사용하여 상품 데이터를 요청합니다.
    """
    # 상품 조회 요청 파라미터 설정
    payload = json.dumps({
        "searchKeywordType": "11816257457"
    })

    # 요청 헤더 설정
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json;charset=UTF-8',
        'Authorization': f'Bearer {token}'
    }

    # HTTP 요청 보내기
    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    conn.request("POST", "/external/v1/products/search", payload, headers)
    res = conn.getresponse()

    # 응답 데이터 출력
    data = res.read()
    print(data.decode("utf-8"))
    conn.close()

def categories_data(token):

    payload = ''
    # 요청 헤더 설정
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json;charset=UTF-8',
        'Authorization': f'Bearer {token}'
    }

    # HTTP 요청 보내기
    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    conn.request("GET", "/external/v1/categories", payload, headers)
    res = conn.getresponse()

    # 응답 데이터 출력
    data = res.read()
    print(data.decode("utf-8"))
    conn.close()

def registry_product(token, product: Product):

    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    payload = json.dumps({
    "originProduct": {
        "statusType": "SALE",               #상품 판매 상태 코드(필수)
        "saleType": "NEW",                  #상품 판매 유형 코드
        "leafCategoryId": "50015040",       #리프 카테고리 ID
        "name": f'{product.title}',         #이름(필수)
        "detailContent": "<!DOCTYPE html>\n<html lang=\"ko\">\n<head>\n  <meta charset=\"UTF-8\">\n  <style>\n    .product-images {\n      display: flex;\n      flex-direction: column;\n      align-items: center;\n    }\n    .product-images img {\n      max-width: 100%;\n      margin-bottom: 10px;\n    }\n    .notice {\n      text-align: center;\n      font-size: 22px;\n      margin-top: 20px;\n      line-height: 1.5;\n      white-space: pre-line;\n    }\n  </style>\n</head>\n<body>\n  <div class=\"product-images\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_01.jpg\" alt=\"목쿠션 이미지 01\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_02.jpg\" alt=\"목쿠션 이미지 02\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_03.jpg\" alt=\"목쿠션 이미지 03\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_04.jpg\" alt=\"목쿠션 이미지 04\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_05.jpg\" alt=\"목쿠션 이미지 05\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_06.jpg\" alt=\"목쿠션 이미지 06\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_07.jpg\" alt=\"목쿠션 이미지 07\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_08.jpg\" alt=\"목쿠션 이미지 08\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_09.jpg\" alt=\"목쿠션 이미지 09\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_10.jpg\" alt=\"목쿠션 이미지 10\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_11.jpg\" alt=\"목쿠션 이미지 11\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_12.jpg\" alt=\"목쿠션 이미지 12\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_13.jpg\" alt=\"목쿠션 이미지 13\">\n    <img src=\"https://wgfood.negagea.kr/주의사항/이염주의_작게.jpg\" alt=\"주의사항\">\n    <img src=\"https://wgfood.negagea.kr/WG마켓/car_neck_pillow/car_neck_pillow_14_00.jpg\" alt=\"목쿠션 이미지 14\">\n  </div>\n\n  <div class=\"notice\">\n    제조사/유통사/3PL 등에서 출고될 수 있는<br>\n    위탁 상품을 취급하고 있습니다.<br>\n    개인정보를 제3자에게 제공할 수 있음을<br>\n    사전에 고지 드립니다.<br>\n    (해당 개인정보는<br>\n    주문 및 배송용으로만 사용되며,<br>\n    물건을 구매 시<br>\n    이에 동의한 것으로 간주합니다)<br>\n  </div>\n</body>\n</html>",
        "images": {                         #필수
        "representativeImage": {            #썸네일
            "url": "https://shop-phinf.pstatic.net/20250510_121/1746866456505qDkId_JPEG/960620823494421_734539260.jpg"
        },
        "optionalImages": [
            {
            "url": "https://shop-phinf.pstatic.net/20250510_121/1746866456505qDkId_JPEG/960620823494421_734539260.jpg"
            }
        ]
        },
        # "saleStartDate": "2024-07-29T15:51:28.071Z",   
        # "saleEndDate": "2024-07-29T15:51:28.071Z",
        "salePrice": f'{(int(int(product.price) * 1.43) // 10) * 10}',
        "stockQuantity": f'{product.inventory}',      #재고
        "deliveryInfo": {
        "deliveryType": "DELIVERY",                     #필수
        "deliveryAttributeType": "NORMAL",              #필수
        "deliveryCompany": "CJGLS",                     #CJ
        # "outboundLocationId": "string",
        # "deliveryBundleGroupUsable": False,
        # "deliveryBundleGroupId": 0,
        # "quickServiceAreas": [
        #     "SEOUL"
        # ],
        # "visitAddressId": 0,
        "deliveryFee": {                #필수
            "deliveryFeeType": "PAID",
            "baseFee": f'{product.baseFee}',
            # "freeConditionalAmount": 0,
            # "repeatQuantity": 0,
            # "secondBaseQuantity": 0,
            # "secondExtraFee": 0,
            # "thirdBaseQuantity": 0,
            # "thirdExtraFee": 0',
            "deliveryFeePayType": "PREPAID",  #배송비 결제 방법
            "deliveryFeeByArea": {
            "deliveryAreaType": "AREA_3",
            "area2extraFee": f'{product.secondExtraFee}',
            "area3extraFee": f'{product.thirdExtraFee}'
            },
            # "differentialFeeByArea": "string"
        },
        "claimDeliveryInfo": {                                                      #필수
            "returnDeliveryCompanyPriorityType": "PRIMARY",
            "returnDeliveryFee": f'{product.baseFee}',                          #반품 배송비(필수)
            "exchangeDeliveryFee": f'{int(product.baseFee) * 2}',                        #교환 배송비(필수)
            # "shippingAddressId": 0,
            # "returnAddressId": 0,
            # "freeReturnInsuranceYn": True
        },
        # "installation": False,
        # "installationFee": False,
        # "expectedDeliveryPeriodType": "ETC",
        # "expectedDeliveryPeriodDirectInput": "string",
        # "todayStockQuantity": 0,
        # "customProductAfterOrderYn": False,
        # "hopeDeliveryGroupId": 0,
        # "businessCustomsClearanceSaleYn": False
        },
        # "productLogistics": [
        # {
        #     "logisticsCompanyId": "string"
        # }
        # ],
        "detailAttribute": {                    #원상품 상세 속성
        "naverShoppingSearchInfo": {
            # "modelId": 0,
            "modelName": f'{product.title}',
            "manufacturerName": f'{product.manufacturerName}',
            # "brandId": 0,
            "brandName": "히카소 마트 협력사"
        },
        # "manufactureDefineNo": "string",
        "afterServiceInfo": {                         #A/S 정보(필수)
            "afterServiceTelephoneNumber": "010-7248-1242",  #A/S 전화번호(필수)
            "afterServiceGuideContent": "제품 이상시 네이버톡톡으로 문의 주시기 바랍니다."      #A/S 안내(필수)
        },
        # "purchaseQuantityInfo": {                             #1인당 구매 수량
        #     "minPurchaseQuantity": 0,
        #     "maxPurchaseQuantityPerId": 0,
        #     "maxPurchaseQuantityPerOrder": 0
        # },
        "originAreaInfo": {                                                 #원산지 정보(필수)
            #"originAreaCode": f'{product.originAreaCode}',                 #원산지 상세 지역 코드(필수) 00(국산), 01(원양산), 02(수입산), 03(기타-상세 설명에 표시), 04(기타-직접 입력), 05(원산지 표기 의무 대상 아님)
            "originAreaCode" : "03",
            "importer": "협력사",
            "content": "중국"
            # "plural": True
        },
        # "sellerCodeInfo": {
        #     "sellerManagementCode": "string",
        #     "sellerBarcode": "string",
        #     "sellerCustomCode1": "string",
        #     "sellerCustomCode2": "string"
        # },
        "optionInfo": {
            "simpleOptionSortType": "CREATE",
            "optionSimple": [
            {
                # "id": 0,
                "groupName": f'{json.loads(product.selectOpt)["groupName"]}',           #옵션명
                "name": name,                                                           #옵션값
                # "usable": True
            }
                for name in json.loads(product.selectOpt)["name"]
            ],
            # "optionCustom": [
            # {
            #     "id": 0,
            #     "groupName": "string",
            #     "name": "string",
            #     "usable": True
            # }
            # ],
        #     "optionCombinationSortType": "CREATE",
        #     "optionCombinationGroupNames": {
        #     "optionGroupName1": "string",
        #     "optionGroupName2": "string",
        #     "optionGroupName3": "string",
        #     "optionGroupName4": "string"
        #     },
        #     "optionCombinations": [
        #     {
        #         "id": 0,
        #         "stockQuantity": 0,
        #         "price": 0,
        #         "usable": True,
        #         "optionName1": "string",
        #         "optionName2": "string",
        #         "optionName3": "string",
        #         "optionName4": "string",
        #         "sellerManagerCode": "string"
        #     }
        #     ],
        #     "standardOptionGroups": [
        #     {
        #         "groupName": "string",
        #         "standardOptionAttributes": [
        #         {
        #             "attributeId": 0,
        #             "attributeValueId": 0,
        #             "attributeValueName": "string",
        #             "imageUrls": [
        #             "string"
        #             ]
        #         }
        #         ]
        #     }
        #     ],
        #     "optionStandards": [
        #     {
        #         "id": 0,
        #         "stockQuantity": 0,
        #         "usable": True,
        #         "optionName1": "string",
        #         "optionName2": "string",
        #         "sellerManagerCode": "string"
        #     }
        #     ],
        #     "useStockManagement": True,
        #     "optionDeliveryAttributes": [
        #     "string"
        #     ]
        },
        # "supplementProductInfo": {
        #     "sortType": "CREATE",
        #     "supplementProducts": [
        #     {
        #         "id": 0,
        #         "groupName": "string",
        #         "name": "string",
        #         "price": 0,
        #         "stockQuantity": 0,
        #         "sellerManagementCode": "string",
        #         "usable": True
        #     }
        #     ]
        # },
        # "purchaseReviewInfo": {
        #     "purchaseReviewExposure": True,
        #     "reviewUnExposeReason": "string"
        # },
        # "isbnInfo": {
        #     "isbn13": "string",
        #     "issn": "string",
        #     "independentPublicationYn": True
        # },
        # "bookInfo": {
        #     "publishDay": "string",
        #     "publisher": {
        #     "code": "string",
        #     "text": "string"
        #     },
        #     "authors": [
        #     {
        #         "code": "string",
        #         "text": "string"
        #     }
        #     ],
        #     "illustrators": [
        #     {
        #         "code": "string",
        #         "text": "string"
        #     }
        #     ],
        #     "translators": [
        #     {
        #         "code": "string",
        #         "text": "string"
        #     }
        #     ]
        # },
        # "eventPhraseCont": "string",
        # "manufactureDate": "2024-07-29",
        # "releaseDate": "2024-07-29",
        # "validDate": "2024-07-29",
        # "taxType": "TAX",
        # "productCertificationInfos": [
        #     {
        #     "certificationInfoId": 0,
        #     "certificationKindType": "KC_CERTIFICATION",
        #     "name": "string",
        #     "certificationNumber": "string",
        #     "certificationMark": True,
        #     "companyName": "string",
        #     "certificationDate": "2024-07-29"
        #     }
        # ],
        # "certificationTargetExcludeContent": {
        #     "childCertifiedProductExclusionYn": True,
        #     "kcExemptionType": "OVERSEAS",
        #     "kcCertifiedProductExclusionYn": "FALSE",
        #     "greenCertifiedProductExclusionYn": True
        # },
        # "sellerCommentContent": "string",
        # "sellerCommentUsable": True,
        "minorPurchasable": True,                       #미성년자 구매 가능 여부(필수)
        # "ecoupon": {
        #     "periodType": "FIXED",
        #     "validStartDate": "2024-07-29",
        #     "validEndDate": "2024-07-29",
        #     "periodDays": 0,
        #     "publicInformationContents": "string",          #E쿠폰 발행처 내용(필수)
        #     "contactInformationContents": "string",         #E쿠폰 연락처 내용(필수)
        #     "usePlaceType": "PLACE",                        #E쿠폰 사용 장소 구분 코드(필수)
        #     "usePlaceContents": "string",                   #사용 장소 내용(필수)
        #     "restrictCart": True,
        #     "siteName": "string"
        # },
        "productInfoProvidedNotice": {
            "productInfoProvidedNoticeType": "ETC",        #상품정보제공고시 상품군 유형(필수)
            # "wear": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "material": "string",
            # "color": "string",
            # "size": "string",
            # "manufacturer": "string",
            # "caution": "string",
            # "packDate": "string",
            # "packDateText": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "shoes": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "material": "string",
            # "color": "string",
            # "size": "string",
            # "height": "string",
            # "manufacturer": "string",
            # "caution": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "bag": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "type": "string",
            # "material": "string",
            # "color": "string",
            # "size": "string",
            # "manufacturer": "string",
            # "caution": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "fashionItems": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "type": "string",
            # "material": "string",
            # "size": "string",
            # "manufacturer": "string",
            # "caution": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "sleepingGear": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "material": "string",
            # "color": "string",
            # "size": "string",
            # "components": "string",
            # "manufacturer": "string",
            # "caution": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "furniture": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "certificationType": "string",
            # "color": "string",
            # "components": "string",
            # "material": "string",
            # "manufacturer": "string",
            # "importer": "string",
            # "producer": "string",
            # "size": "string",
            # "installedCharge": "string",
            # "warrantyPolicy": "string",
            # "refurb": "string",
            # "afterServiceDirector": "string"
            # },
            # "imageAppliances": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "ratedVoltage": "string",
            # "powerConsumption": "string",
            # "energyEfficiencyRating": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "size": "string",
            # "additionalCost": "string",
            # "displaySpecification": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "homeAppliances": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "ratedVoltage": "string",
            # "powerConsumption": "string",
            # "energyEfficiencyRating": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "size": "string",
            # "additionalCost": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "seasonAppliances": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "ratedVoltage": "string",
            # "powerConsumption": "string",
            # "energyEfficiencyRating": "string",
            # "releaseDate": {
            #     "year": 0,
            #     "month": "JANUARY",
            #     "monthValue": 0,
            #     "leapYear": True
            # },
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "size": "string",
            # "area": "string",
            # "installedCharge": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "officeAppliances": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "ratedVoltage": "string",
            # "powerConsumption": "string",
            # "energyEfficiencyRating": "string",
            # "releaseDate": {
            #     "year": 0,
            #     "month": "JANUARY",
            #     "monthValue": 0,
            #     "leapYear": True
            # },
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "size": "string",
            # "weight": "string",
            # "specification": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "opticsAppliances": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "size": "string",
            # "weight": "string",
            # "specification": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "microElectronics": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "ratedVoltage": "string",
            # "powerConsumption": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "size": "string",
            # "weight": "string",
            # "specification": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "navigation": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "ratedVoltage": "string",
            # "powerConsumption": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "size": "string",
            # "weight": "string",
            # "specification": "string",
            # "updateCost": "string",
            # "freeCostPeriod": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "carArticles": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "certificationType": "string",
            # "caution": "string",
            # "manufacturer": "string",
            # "size": "string",
            # "applyModel": "string",
            # "warrantyPolicy": "string",
            # "roadWorthyCertification": "string",
            # "afterServiceDirector": "string"
            # },
            # "medicalAppliances": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "licenceNo": "string",
            # "advertisingCertificationType": "string",
            # "ratedVoltage": "string",
            # "powerConsumption": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "purpose": "string",
            # "usage": "string",
            # "caution": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "kitchenUtensils": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "material": "string",
            # "component": "string",
            # "size": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "producer": "string",
            # "importDeclaration": True,
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "cosmetic": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "capacity": "string",
            # "specification": "string",
            # "expirationDate": "string",
            # "expirationDateText": "string",
            # "usage": "string",
            # "manufacturer": "string",
            # "producer": "string",
            # "distributor": "string",
            # "customizedDistributor": "string",
            # "mainIngredient": "string",
            # "certificationType": "string",
            # "caution": "string",
            # "warrantyPolicy": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "jewellery": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "material": "string",
            # "purity": "string",
            # "bandMaterial": "string",
            # "weight": "string",
            # "manufacturer": "string",
            # "producer": "string",
            # "size": "string",
            # "caution": "string",
            # "specification": "string",
            # "provideWarranty": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "food": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "foodItem": "string",
            # "weight": "string",
            # "amount": "string",
            # "size": "string",
            # "packDate": "2024-07-29",
            # "packDateText": "string",
            # "consumptionDate": "2024-07-29",
            # "consumptionDateText": "string",
            # "producer": "string",
            # "relevantLawContent": "string",
            # "productComposition": "string",
            # "keep": "string",
            # "adCaution": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "generalFood": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "productName": "string",
            # "foodType": "string",
            # "producer": "string",
            # "location": "string",
            # "packDate": "2024-07-29",
            # "packDateText": "string",
            # "consumptionDate": "2024-07-29",
            # "consumptionDateText": "string",
            # "weight": "string",
            # "amount": "string",
            # "ingredients": "string",
            # "nutritionFacts": "string",
            # "geneticallyModified": True,
            # "consumerSafetyCaution": "string",
            # "importDeclarationCheck": True,
            # "customerServicePhoneNumber": "string"
            # },
            # "dietFood": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "productName": "string",
            # "producer": "string",
            # "location": "string",
            # "consumptionDate": "2024-07-29",
            # "consumptionDateText": "string",
            # "storageMethod": "string",
            # "weight": "string",
            # "amount": "string",
            # "ingredients": "string",
            # "nutritionFacts": "string",
            # "specification": "string",
            # "cautionAndSideEffect": "string",
            # "nonMedicinalUsesMessage": "string",
            # "geneticallyModified": True,
            # "importDeclarationCheck": True,
            # "consumerSafetyCaution": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "kids": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "size": "string",
            # "weight": "string",
            # "color": "string",
            # "material": "string",
            # "recommendedAge": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "caution": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string",
            # "numberLimit": "string"
            # },
            # "musicalInstrument": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "size": "string",
            # "color": "string",
            # "material": "string",
            # "components": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "detailContent": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "sportsEquipment": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "size": "string",
            # "weight": "string",
            # "color": "string",
            # "material": "string",
            # "components": "string",
            # "releaseDate": {
            #     "year": 0,
            #     "month": "JANUARY",
            #     "monthValue": 0,
            #     "leapYear": True
            # },
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "detailContent": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            # "books": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "title": "string",
            # "author": "string",
            # "publisher": "string",
            # "size": "string",
            # "pages": "string",
            # "components": "string",
            # "publishDate": "2024-07-29",
            # "publishDateText": "string",
            # "description": "string"
            # },
            # "rentalEtc": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "ownershipTransferCondition": "string",
            # "payingForLossOrDamage": "string",
            # "refundPolicyForCancel": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "rentalHa": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "ownershipTransferCondition": "string",
            # "payingForLossOrDamage": "string",
            # "refundPolicyForCancel": "string",
            # "customerServicePhoneNumber": "string",
            # "maintenance": "string",
            # "specification": "string"
            # },
            # "digitalContents": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "producer": "string",
            # "termsOfUse": "string",
            # "usePeriod": "string",
            # "medium": "string",
            # "requirement": "string",
            # "cancelationPolicy": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "giftCard": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "issuer": "string",
            # "periodStartDate": "2024-07-29",
            # "periodEndDate": "2024-07-29",
            # "periodDays": 0,
            # "termsOfUse": "string",
            # "useStorePlace": "string",
            # "useStoreAddressId": 0,
            # "useStoreUrl": "string",
            # "refundPolicy": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "mobileCoupon": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "issuer": "string",
            # "usableCondition": "string",
            # "usableStore": "string",
            # "cancelationPolicy": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "movieShow": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "sponsor": "string",
            # "actor": "string",
            # "rating": "string",
            # "showTime": "string",
            # "showPlace": "string",
            # "cancelationCondition": "string",
            # "cancelationPolicy": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "etcService": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "serviceProvider": "string",
            # "certificateDetails": "string",
            # "usableCondition": "string",
            # "cancelationStandard": "string",
            # "cancelationPolicy": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "biochemistry": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "productName": "string",
            # "dosageForm": "string",
            # "packDate": "string",
            # "packDateText": "string",
            # "expirationDate": "string",
            # "expirationDateText": "string",
            # "weight": "string",
            # "effect": "string",
            # "importer": "string",
            # "producer": "string",
            # "manufacturer": "string",
            # "childProtection": "string",
            # "chemicals": "string",
            # "caution": "string",
            # "safeCriterionNo": "string",
            # "customerServicePhoneNumber": "string"
            # },
            # "biocidal": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "productName": "string",
            # "weight": "string",
            # "effect": "string",
            # "rangeOfUse": "string",
            # "importer": "string",
            # "producer": "string",
            # "manufacturer": "string",
            # "childProtection": "string",
            # "harmfulChemicalSubstance": "string",
            # "maleficence": "string",
            # "caution": "string",
            # "approvalNumber": "string",
            # "customerServicePhoneNumber": "string",
            # "expirationDate": "2024-07-29",
            # "expirationDateText": "string"
            # },
            # "cellPhone": {
            # "returnCostReason": "string",
            # "noRefundReason": "string",
            # "qualityAssuranceStandard": "string",
            # "compensationProcedure": "string",
            # "troubleShootingContents": "string",
            # "itemName": "string",
            # "modelName": "string",
            # "certificationType": "string",
            # "releaseDate": "string",
            # "releaseDateText": "string",
            # "manufacturer": "string",
            # "importer": "string",
            # "producer": "string",
            # "size": "string",
            # "weight": "string",
            # "telecomType": "string",
            # "joinProcess": "string",
            # "extraBurden": "string",
            # "specification": "string",
            # "warrantyPolicy": "string",
            # "afterServiceDirector": "string"
            # },
            "etc": {
            "returnCostReason": 0,
            "noRefundReason": 0,
            "qualityAssuranceStandard": 0,
            "compensationProcedure": 0,
            "troubleShootingContents": 0,
            "itemName": "상품상세참조",
            "modelName": "상품상세참조",
            "certificateDetails": "상품상세참조",
            "manufacturer": "상품상세참조",
            "afterServiceDirector": "상품상세참조",
            # "customerServicePhoneNumber": "string"
            }
        },
        # "productAttributes": [
        #     {
        #     "attributeSeq": 0,
        #     "attributeValueSeq": 0,
        #     "attributeRealValue": "string",
        #     "attributeRealValueUnitCode": "string"
        #     }
        # ],
        # "cultureCostIncomeDeductionYn": True,
        # "customProductYn": True,
        # "itselfProductionProductYn": True,
        # "brandCertificationYn": True,
        # "seoInfo": {
        #     "pageTitle": "string",
        #     "metaDescription": "string",
        #     "sellerTags": [
        #     {
        #         "code": 0,
        #         "text": "string"
        #     }
        #     ]
        # },
        # "productSize": {
        #     "sizeTypeNo": 0,
        #     "sizeAttributes": [
        #     {
        #         "name": "string",
        #         "sizeValues": [
        #         {
        #             "sizeValueTypeNo": 0,
        #             "value": 0
        #         }
        #         ]
        #     }
        #     ],
        #     "models": [
        #     {
        #         "modelId": 0
        #     }
        #     ]
        # }
        },
        "customerBenefit": {
        "immediateDiscountPolicy": {
            "discountMethod": {
            "value": 17,
            "unitType": "PERCENT"
            # "startDate": "2024-07-29T15:51:28.071Z",
            # "endDate": "2024-07-29T15:51:28.071Z"
            }
        },
        # "purchasePointPolicy": {
        #     "value": 0,
        #     "unitType": "PERCENT",
        #     "startDate": "2024-07-29",
        #     "endDate": "2024-07-29"
        # },
        "reviewPointPolicy": {
            "textReviewPoint": 100,
            "photoVideoReviewPoint": 200
            # "afterUseTextReviewPoint": 0,
            # "afterUsePhotoVideoReviewPoint": 0,
            # "storeMemberReviewPoint": 0,
            # "startDate": "2024-07-29",
            # "endDate": "2024-07-29"
        },
        # "freeInterestPolicy": {
        #     "value": 0,
        #     "startDate": "2024-07-29",
        #     "endDate": "2024-07-29"
        # },
        # "giftPolicy": {
        #     "presentContent": "string"
        # },
        # "multiPurchaseDiscountPolicy": {
        #     "discountMethod": {
        #     "value": 0,
        #     "unitType": "PERCENT",
        #     "startDate": "2024-07-29",
        #     "endDate": "2024-07-29"
        #     },
        #     "orderValue": 0,
        #     "orderValueUnitType": "PERCENT"
        # },
        # "reservedDiscountPolicy": {
        #     "discountMethod": {
        #     "value": 0,
        #     "unitType": "PERCENT",
        #     "startDate": "2024-07-29T15:51:28.071Z",
        #     "endDate": "2024-07-29T15:51:28.071Z"
        #     }
        # }
        }
    },
    "smartstoreChannelProduct": {
        # "channelProductName": "string",
        # "bbsSeq": 0,
        # "storeKeepExclusiveProduct": True,
        "naverShoppingRegistration": True,
        "channelProductDisplayStatusType": "ON"
    },
    # "windowChannelProduct": {
    #     "channelProductName": "string",
    #     "bbsSeq": 0,
    #     "storeKeepExclusiveProduct": True,
    #     "naverShoppingRegistration": True,
    #     "channelNo": 0,
    #     "best": True
    # }
    })
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json;charset=UTF-8',
    'Authorization': f'Bearer {token}'
    }
    conn.request("POST", "/external/v2/products", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))

def main():
    """
    메인 함수: 토큰을 받고, 상품 데이터를 요청하는 전체 흐름을 처리합니다.
    """
    # 도메꾹 상품 조회(detail)
    product = domeggook_search_product()
    # access_token 얻기
    token = get_access_token(client_id, client_secret)
    
    # 상품 데이터 요청
    # fetch_product_data(token)

    #카테고리 조회
    # categories_data(token)
    #상품 이미지 다건 등록
    # registry_image(token)
    #상품등록
    registry_product(token, product)

if __name__ == "__main__":
    main()
