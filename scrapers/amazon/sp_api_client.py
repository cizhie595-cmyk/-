"""
Amazon SP-API 官方接口客户端

通过用户自备的 SP-API 凭证（BYOK 模式），合规获取亚马逊数据。
支持: Catalog Items API, Product Pricing API, Reports API 等。

使用前需要用户在 API 配置中心填入:
  - LWA Client ID
  - LWA Client Secret
  - Refresh Token
  - AWS Access Key / Secret Key
  - Marketplace ID
"""

import time
import json
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import requests

from utils.logger import get_logger

logger = get_logger()


# Amazon 站点 Marketplace ID 映射
MARKETPLACE_IDS = {
    "US": "ATVPDKIKX0DER",
    "CA": "A2EUQ1WTGCTBG2",
    "MX": "A1AM78C64UM0Y8",
    "UK": "A1F83G8C2ARO7P",
    "DE": "A1PA6795UKMFR9",
    "FR": "A13V1IB3VIYZZH",
    "IT": "APJ6JRA9NG5V4",
    "ES": "A1RKKUPIHCS9HS",
    "JP": "A1VC38T7YXB528",
    "AU": "A39IBJ37TRP1C6",
    "AE": "A2VIGQ35RCS4UG",
    "SG": "A19VAU5U5O7RUS",
}

# SP-API 端点映射
SP_API_ENDPOINTS = {
    "US": "https://sellingpartnerapi-na.amazon.com",
    "CA": "https://sellingpartnerapi-na.amazon.com",
    "MX": "https://sellingpartnerapi-na.amazon.com",
    "UK": "https://sellingpartnerapi-eu.amazon.com",
    "DE": "https://sellingpartnerapi-eu.amazon.com",
    "FR": "https://sellingpartnerapi-eu.amazon.com",
    "IT": "https://sellingpartnerapi-eu.amazon.com",
    "ES": "https://sellingpartnerapi-eu.amazon.com",
    "JP": "https://sellingpartnerapi-fe.amazon.com",
    "AU": "https://sellingpartnerapi-fe.amazon.com",
    "AE": "https://sellingpartnerapi-eu.amazon.com",
    "SG": "https://sellingpartnerapi-fe.amazon.com",
}


class AmazonSPAPIClient:
    """
    Amazon Selling Partner API 客户端

    封装 SP-API 的认证流程（LWA OAuth + AWS Signature V4），
    提供 Catalog、Pricing、Reports 等接口的调用方法。
    """

    def __init__(self, credentials: dict, marketplace: str = "US"):
        """
        :param credentials: SP-API 凭证字典，包含:
            - lwa_client_id: LWA 应用客户端 ID
            - lwa_client_secret: LWA 应用客户端密钥
            - refresh_token: 卖家授权的 Refresh Token
            - aws_access_key: AWS IAM 用户 Access Key
            - aws_secret_key: AWS IAM 用户 Secret Key
            - role_arn: (可选) IAM Role ARN
        :param marketplace: 目标站点代码 (US, UK, DE, JP 等)
        """
        self.credentials = credentials
        self.marketplace = marketplace.upper()
        self.marketplace_id = MARKETPLACE_IDS.get(self.marketplace, MARKETPLACE_IDS["US"])
        self.endpoint = SP_API_ENDPOINTS.get(self.marketplace, SP_API_ENDPOINTS["US"])

        self._access_token = None
        self._token_expires_at = 0

        logger.info(f"[SP-API] 初始化客户端 | 站点: {self.marketplace} | Marketplace ID: {self.marketplace_id}")

    # ================================================================
    # LWA OAuth 2.0 认证
    # ================================================================

    def _get_access_token(self) -> str:
        """
        通过 LWA (Login with Amazon) 获取 Access Token。
        Token 有效期为 3600 秒，自动缓存和刷新。
        """
        now = time.time()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        url = "https://api.amazon.com/auth/o2/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.credentials.get("refresh_token", ""),
            "client_id": self.credentials.get("lwa_client_id", ""),
            "client_secret": self.credentials.get("lwa_client_secret", ""),
        }

        try:
            resp = requests.post(url, data=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expires_at = now + data.get("expires_in", 3600)
            logger.info("[SP-API] LWA Access Token 获取成功")
            return self._access_token
        except Exception as e:
            logger.error(f"[SP-API] LWA 认证失败: {e}")
            raise ConnectionError(f"Amazon SP-API 认证失败: {e}")

    # ================================================================
    # AWS Signature V4 签名
    # ================================================================

    def _sign_request(self, method: str, url: str, headers: dict,
                      payload: str = "") -> dict:
        """
        使用 AWS Signature V4 对请求进行签名。
        """
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        path = parsed.path or "/"
        query = parsed.query

        now = datetime.now(timezone.utc)
        datestamp = now.strftime("%Y%m%d")
        amzdate = now.strftime("%Y%m%dT%H%M%SZ")
        region = self._get_region()
        service = "execute-api"

        aws_access_key = self.credentials.get("aws_access_key", "")
        aws_secret_key = self.credentials.get("aws_secret_key", "")

        # Step 1: 创建规范请求
        headers["host"] = host
        headers["x-amz-date"] = amzdate

        signed_headers_list = sorted(headers.keys())
        signed_headers = ";".join(signed_headers_list)
        canonical_headers = "".join(
            f"{k}:{headers[k]}\n" for k in signed_headers_list
        )

        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = (
            f"{method}\n{path}\n{query}\n{canonical_headers}\n"
            f"{signed_headers}\n{payload_hash}"
        )

        # Step 2: 创建待签名字符串
        credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n{amzdate}\n{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        # Step 3: 计算签名
        def _hmac_sha256(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        signing_key = _hmac_sha256(
            _hmac_sha256(
                _hmac_sha256(
                    _hmac_sha256(
                        f"AWS4{aws_secret_key}".encode("utf-8"),
                        datestamp
                    ),
                    region
                ),
                service
            ),
            "aws4_request"
        )
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Step 4: 构建 Authorization Header
        headers["Authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={aws_access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        return headers

    def _get_region(self) -> str:
        """根据站点返回 AWS 区域"""
        region_map = {
            "US": "us-east-1", "CA": "us-east-1", "MX": "us-east-1",
            "UK": "eu-west-1", "DE": "eu-west-1", "FR": "eu-west-1",
            "IT": "eu-west-1", "ES": "eu-west-1",
            "JP": "us-west-2", "AU": "us-west-2", "SG": "us-west-2",
            "AE": "eu-west-1",
        }
        return region_map.get(self.marketplace, "us-east-1")

    # ================================================================
    # 通用请求方法
    # ================================================================

    def _request(self, method: str, path: str, params: dict = None,
                 body: dict = None) -> dict:
        """
        发送已签名的 SP-API 请求。
        """
        access_token = self._get_access_token()
        url = f"{self.endpoint}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {
            "x-amz-access-token": access_token,
            "content-type": "application/json",
            "user-agent": "AmazonSellerTool/1.0 (Language=Python)",
        }

        payload = json.dumps(body) if body else ""
        headers = self._sign_request(method, url, headers, payload)

        try:
            resp = requests.request(
                method, url, headers=headers,
                data=payload if body else None,
                timeout=30
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2))
                logger.warning(f"[SP-API] 限流，{retry_after}秒后重试")
                time.sleep(retry_after)
                return self._request(method, path, params, body)

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"[SP-API] HTTP 错误: {e} | Response: {resp.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"[SP-API] 请求失败: {e}")
            raise

    # ================================================================
    # Catalog Items API - 商品目录
    # ================================================================

    def search_catalog(self, keywords: str, max_results: int = 50,
                       included_data: list = None) -> list[dict]:
        """
        通过关键词搜索亚马逊商品目录。

        :param keywords: 搜索关键词
        :param max_results: 最大返回数量
        :param included_data: 需要包含的数据类型
            (identifiers, images, productTypes, salesRanks, summaries, etc.)
        :return: 商品列表
        """
        if included_data is None:
            included_data = [
                "identifiers", "images", "productTypes",
                "salesRanks", "summaries",
            ]

        all_items = []
        page_token = None

        while len(all_items) < max_results:
            params = {
                "keywords": keywords,
                "marketplaceIds": self.marketplace_id,
                "includedData": ",".join(included_data),
                "pageSize": min(20, max_results - len(all_items)),
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                data = self._request("GET", "/catalog/2022-04-01/items", params=params)
                items = data.get("items", [])
                all_items.extend(self._parse_catalog_items(items))

                pagination = data.get("pagination", {})
                page_token = pagination.get("nextToken")
                if not page_token:
                    break

            except Exception as e:
                logger.error(f"[SP-API] 搜索目录失败: {e}")
                break

        logger.info(f"[SP-API] 关键词 '{keywords}' 搜索到 {len(all_items)} 个商品")
        return all_items[:max_results]

    def get_catalog_item(self, asin: str, included_data: list = None) -> Optional[dict]:
        """
        获取单个 ASIN 的详细目录信息。
        """
        if included_data is None:
            included_data = [
                "attributes", "dimensions", "identifiers", "images",
                "productTypes", "relationships", "salesRanks", "summaries",
            ]

        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": ",".join(included_data),
        }

        try:
            data = self._request("GET", f"/catalog/2022-04-01/items/{asin}", params=params)
            return self._parse_single_catalog_item(data)
        except Exception as e:
            logger.error(f"[SP-API] 获取 ASIN {asin} 失败: {e}")
            return None

    def _parse_catalog_items(self, items: list) -> list[dict]:
        """解析 Catalog Items API 返回的商品列表"""
        parsed = []
        for item in items:
            parsed.append(self._parse_single_catalog_item(item))
        return parsed

    def _parse_single_catalog_item(self, item: dict) -> dict:
        """解析单个商品的目录数据"""
        asin = item.get("asin", "")

        # 提取摘要信息
        summaries = item.get("summaries", [])
        summary = summaries[0] if summaries else {}

        # 提取图片
        images_data = item.get("images", [])
        images = []
        for img_set in images_data:
            for img in img_set.get("images", []):
                images.append({
                    "url": img.get("link", ""),
                    "variant": img.get("variant", "MAIN"),
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                })

        # 提取 BSR 排名
        sales_ranks = item.get("salesRanks", [])
        bsr_list = []
        for rank_set in sales_ranks:
            for rank in rank_set.get("ranks", []):
                bsr_list.append({
                    "category": rank.get("title", ""),
                    "rank": rank.get("value", 0),
                    "link": rank.get("link", ""),
                })

        return {
            "asin": asin,
            "title": summary.get("itemName", ""),
            "brand": summary.get("brand", ""),
            "manufacturer": summary.get("manufacturer", ""),
            "product_type": summary.get("productType", ""),
            "category_node": summary.get("browseClassification", {}).get("displayName", ""),
            "images": images,
            "main_image": images[0]["url"] if images else "",
            "bsr_ranks": bsr_list,
            "bsr": bsr_list[0]["rank"] if bsr_list else 0,
            "url": f"https://www.amazon.com/dp/{asin}",
            "source": "sp-api",
        }

    # ================================================================
    # Product Pricing API - 价格
    # ================================================================

    def get_competitive_pricing(self, asins: list[str]) -> dict:
        """
        获取竞争价格信息（含 Buy Box 价格）。

        :param asins: ASIN 列表（最多 20 个）
        :return: {asin: pricing_info} 字典
        """
        results = {}
        # SP-API 每次最多 20 个 ASIN
        for i in range(0, len(asins), 20):
            batch = asins[i:i+20]
            params = {
                "MarketplaceId": self.marketplace_id,
                "ItemType": "Asin",
                "Asins": ",".join(batch),
            }

            try:
                data = self._request(
                    "GET",
                    "/products/pricing/v0/competitivePrice",
                    params=params
                )
                for item in data.get("payload", []):
                    asin = item.get("ASIN", "")
                    product = item.get("Product", {})
                    competitive = product.get("CompetitivePricing", {})
                    prices = competitive.get("CompetitivePrices", [])

                    buy_box_price = None
                    for p in prices:
                        if p.get("belongsToRequester", False) or p.get("condition", "") == "New":
                            price_obj = p.get("Price", {})
                            listing = price_obj.get("ListingPrice", {})
                            buy_box_price = float(listing.get("Amount", 0))
                            break

                    results[asin] = {
                        "buy_box_price": buy_box_price,
                        "number_of_offer_listings": competitive.get(
                            "NumberOfOfferListings", []
                        ),
                    }

            except Exception as e:
                logger.error(f"[SP-API] 获取竞争价格失败: {e}")

        return results

    # ================================================================
    # Reports API - 报告
    # ================================================================

    def request_report(self, report_type: str, data_start_time: str = None,
                       data_end_time: str = None) -> Optional[str]:
        """
        请求生成报告。

        :param report_type: 报告类型
            - GET_MERCHANT_LISTINGS_ALL_DATA: 全部在售商品
            - GET_FLAT_FILE_OPEN_LISTINGS_DATA: 在售商品（平面文件）
            - GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT: 搜索词报告
        :return: 报告 ID
        """
        body = {
            "reportType": report_type,
            "marketplaceIds": [self.marketplace_id],
        }
        if data_start_time:
            body["dataStartTime"] = data_start_time
        if data_end_time:
            body["dataEndTime"] = data_end_time

        try:
            data = self._request("POST", "/reports/2021-06-30/reports", body=body)
            report_id = data.get("reportId", "")
            logger.info(f"[SP-API] 报告请求已提交 | ID: {report_id} | 类型: {report_type}")
            return report_id
        except Exception as e:
            logger.error(f"[SP-API] 请求报告失败: {e}")
            return None

    def get_report(self, report_id: str) -> Optional[dict]:
        """获取报告状态和下载链接"""
        try:
            return self._request("GET", f"/reports/2021-06-30/reports/{report_id}")
        except Exception as e:
            logger.error(f"[SP-API] 获取报告状态失败: {e}")
            return None

    def download_report(self, report_document_id: str) -> Optional[str]:
        """下载报告内容"""
        try:
            data = self._request(
                "GET",
                f"/reports/2021-06-30/documents/{report_document_id}"
            )
            download_url = data.get("url", "")
            if download_url:
                resp = requests.get(download_url, timeout=60)
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            logger.error(f"[SP-API] 下载报告失败: {e}")
        return None
