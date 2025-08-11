"""123云盘API客户端模块"""
import asyncio
import hashlib
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Callable

import httpx
from loguru import logger


class Pan123AuthError(Exception):
    """123云盘认证错误"""
    pass


class Pan123APIError(Exception):
    """123云盘API错误"""
    pass


class Pan123Client:
    """123云盘API客户端"""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        初始化123云盘客户端
        
        Args:
            client_id: 客户端ID
            client_secret: 客户端密钥
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://open-api.123pan.com"
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.session: Optional[httpx.AsyncClient] = None
        self._auth_lock = asyncio.Lock()  # 用于令牌刷新的并发控制
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._init_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._close_session()
        
    async def _init_session(self):
        """初始化HTTP会话"""
        if not self.session:
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=30.0,  # 连接超时
                    read=300.0,    # 读取超时（5分钟，适用于大文件上传）
                    write=300.0,   # 写入超时
                    pool=30.0      # 连接池超时
                ),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
            
    async def _close_session(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.aclose()
            self.session = None
            
    async def _ensure_session(self):
        """确保HTTP会话已初始化"""
        if not self.session:
            await self._init_session()
            
    def _get_common_headers(self) -> Dict[str, str]:
        """获取通用请求头"""
        headers = {
            "Platform": "open_platform",
            "Content-Type": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
        
    async def _request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法
            url: 请求URL
            headers: 额外请求头
            **kwargs: 其他请求参数
            
        Returns:
            API响应数据
            
        Raises:
            Pan123APIError: API请求错误
        """
        await self._ensure_session()
        
        request_headers = self._get_common_headers()
        if headers:
            request_headers.update(headers)
            
        full_url = url if url.startswith("http") else f"{self.base_url}{url}"
        
        try:
            response = await self.session.request(
                method=method,
                url=full_url,
                headers=request_headers,
                **kwargs
            )
            response.raise_for_status()
            
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                if data.get("code") != 0:
                    raise Pan123APIError(f"API错误: {data.get('message', 'Unknown error')}")
                return data.get("data", {})
            else:
                return {"raw_response": response.content}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
            raise Pan123APIError(f"HTTP错误: {e.response.status_code}")
        except httpx.RequestError as e:
            error_msg = f"网络请求失败: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            raise Pan123APIError(error_msg)
            
    def _is_token_expired(self) -> bool:
        """检查token是否过期"""
        if not self.token_expires_at:
            return True
        
        # 获取当前时间并处理时区问题
        now = datetime.now()
        expires_at = self.token_expires_at
        
        # 如果过期时间有时区信息，将其转换为本地时间（不带时区）
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        
        # 提前5分钟刷新token
        return now >= (expires_at - timedelta(minutes=5))
        
    async def authenticate(self) -> str:
        """
        获取访问令牌
        
        Returns:
            访问令牌
            
        Raises:
            Pan123AuthError: 认证失败
        """
        # 快速检查，如果令牌有效直接返回
        if self.access_token and not self._is_token_expired():
            return self.access_token
            
        # 使用锁确保同一时间只有一个请求进行认证
        async with self._auth_lock:
            # 再次检查，可能在等待锁期间已经被其他请求刷新了
            if self.access_token and not self._is_token_expired():
                return self.access_token
                
            logger.info("正在获取123云盘访问令牌...")
            
            payload = {
                "clientID": self.client_id,
                "clientSecret": self.client_secret
            }
            
            try:
                data = await self._request("POST", "/api/v1/access_token", json=payload)
                
                self.access_token = data.get("accessToken")
                if not self.access_token:
                    raise Pan123AuthError("未能获取访问令牌")
                    
                # 解析过期时间
                expired_at_str = data.get("expiredAt")
                if expired_at_str:
                    try:
                        self.token_expires_at = datetime.fromisoformat(expired_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        # 如果解析失败，默认设置30天后过期
                        self.token_expires_at = datetime.now() + timedelta(days=30)
                else:
                    self.token_expires_at = datetime.now() + timedelta(days=30)
                    
                logger.info(f"123云盘令牌获取成功，过期时间: {self.token_expires_at}")
                return self.access_token
                
            except Exception as e:
                logger.error(f"123云盘认证失败: {e}")
                raise Pan123AuthError(f"认证失败: {e}")
            
    async def get_upload_domains(self) -> List[str]:
        """
        获取上传域名列表
        
        Returns:
            上传域名列表
            
        Raises:
            Pan123APIError: 获取上传域名失败
        """
        await self.authenticate()
        data = await self._request("GET", "/upload/v2/file/domain")
        # API返回的是数组，而不是在servers字段中
        if isinstance(data, list):
            return data
        return data.get("servers", data)
        
    async def get_file_list(self, parent_id: int = 0, limit: int = 100) -> List[Dict]:
        """
        获取文件列表
        
        Args:
            parent_id: 父目录ID，0为根目录
            limit: 返回文件数量限制
            
        Returns:
            文件列表
            
        Raises:
            Pan123APIError: 获取文件列表失败
        """
        await self.authenticate()
        
        params = {
            "parentFileId": parent_id,
            "limit": limit
        }
        
        data = await self._request("GET", "/api/v2/file/list", params=params)
        return data.get("fileList", [])
        
    async def create_folder(self, parent_id: int, name: str) -> int:
        """
        创建文件夹，如果已存在则返回现有的文件夹ID
        
        Args:
            parent_id: 父目录ID
            name: 文件夹名称
            
        Returns:
            文件夹ID（新创建的或已存在的）
            
        Raises:
            Pan123APIError: 创建文件夹失败
        """
        await self.authenticate()
        
        # 首先尝试获取现有文件夹
        try:
            files = await self.get_file_list(parent_id)
            for file_info in files:
                if (file_info.get("type") == 1 and  # 1表示文件夹
                    file_info.get("filename") == name and
                    file_info.get("trashed") == 0):  # 未在回收站
                    existing_id = file_info.get("fileId")
                    logger.debug(f"文件夹已存在: {name} (ID: {existing_id})")
                    return existing_id
        except Exception as e:
            logger.warning(f"获取文件列表失败，尝试直接创建: {e}")
        
        # 文件夹不存在，创建新文件夹
        payload = {
            "name": name,
            "parentID": parent_id
        }
        
        try:
            data = await self._request("POST", "/upload/v1/file/mkdir", json=payload)
            folder_id = data.get("dirID")
            if not folder_id:
                raise Pan123APIError(f"创建文件夹失败: {name}")
                
            logger.debug(f"创建文件夹成功: {name} (ID: {folder_id})")
            return folder_id
            
        except Pan123APIError as e:
            # 如果是文件夹已存在的错误，再次尝试获取
            if "已经有同名文件夹" in str(e):
                try:
                    files = await self.get_file_list(parent_id)
                    for file_info in files:
                        if (file_info.get("type") == 1 and  # 1表示文件夹
                            file_info.get("filename") == name and
                            file_info.get("trashed") == 0):  # 未在回收站
                            existing_id = file_info.get("fileId")
                            logger.debug(f"创建失败但找到已存在文件夹: {name} (ID: {existing_id})")
                            return existing_id
                except Exception:
                    pass
            raise e
        
    async def create_file(
        self, 
        parent_id: int, 
        filename: str, 
        etag: str, 
        size: int,
        duplicate: int = 1
    ) -> Dict:
        """
        创建文件（检测秒传）
        
        Args:
            parent_id: 父目录ID
            filename: 文件名
            etag: 文件MD5值
            size: 文件大小（字节）
            duplicate: 重名策略（1保留两者，2覆盖）
            
        Returns:
            创建文件结果
            
        Raises:
            Pan123APIError: 创建文件失败
        """
        await self.authenticate()
        
        payload = {
            "parentFileID": parent_id,
            "filename": filename,
            "etag": etag,
            "size": size,
            "duplicate": duplicate,
            "containDir": False
        }
        
        data = await self._request("POST", "/upload/v2/file/create", json=payload)
        logger.debug(f"创建文件响应: {filename} -> {data}")
        return data
        
    async def upload_single(
        self,
        upload_domain: str,
        file_path: str,
        parent_id: int,
        filename: str,
        etag: str,
        size: int,
        duplicate: int = 1,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        单步上传文件
        
        Args:
            upload_domain: 上传域名
            file_path: 本地文件路径
            parent_id: 父目录ID
            filename: 文件名
            etag: 文件MD5
            size: 文件大小
            duplicate: 重名策略
            progress_callback: 进度回调函数
            
        Returns:
            上传结果
            
        Raises:
            Pan123APIError: 上传失败
        """
        await self.authenticate()
        
        url = f"{upload_domain}/upload/v2/file/single/create"
        
        # 准备表单数据
        data = {
            "parentFileID": str(parent_id),
            "filename": filename,
            "etag": etag,
            "size": str(size),
            "duplicate": str(duplicate),
            "containDir": "false"
        }
        
        logger.debug(f"单步上传参数: parent_id={parent_id}, filename={filename}, size={size}")
        
        # 准备文件数据 - 对于大文件使用文件句柄，小文件读取到内存
        file_handle = None
        try:
            if size > 100 * 1024 * 1024:  # 超过100MB使用文件句柄
                file_handle = open(file_path, 'rb')
                files = {"file": (filename, file_handle, "application/octet-stream")}
            else:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                files = {"file": (filename, file_content, "application/octet-stream")}
            
            # 移除JSON Content-Type，让httpx自动设置multipart/form-data
            headers = self._get_common_headers()
            if "Content-Type" in headers:
                del headers["Content-Type"]
                
            response_data = await self._request(
                "POST", url, headers=headers, data=data, files=files
            )
        finally:
            # 确保文件句柄被关闭
            if file_handle:
                file_handle.close()
            
        logger.debug(f"单步上传完成: {filename}")
        return response_data
        
    async def upload_slice(
        self,
        upload_domain: str,
        preupload_id: str,
        slice_no: int,
        slice_data: bytes,
        slice_md5: str
    ) -> bool:
        """
        上传分片
        
        Args:
            upload_domain: 上传域名
            preupload_id: 预上传ID
            slice_no: 分片序号
            slice_data: 分片数据
            slice_md5: 分片MD5
            
        Returns:
            是否上传成功
            
        Raises:
            Pan123APIError: 分片上传失败
        """
        await self.authenticate()
        
        url = f"{upload_domain}/upload/v2/file/slice"
        
        # 准备表单数据
        data = {
            "preuploadID": preupload_id,
            "sliceNo": str(slice_no),
            "sliceMD5": slice_md5
        }
        
        # 准备分片文件
        files = {"slice": ("slice", slice_data, "application/octet-stream")}
        
        # 移除JSON Content-Type
        headers = self._get_common_headers()
        if "Content-Type" in headers:
            del headers["Content-Type"]
            
        # 添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self._request("POST", url, headers=headers, data=data, files=files)
                logger.debug(f"分片上传成功: {slice_no}")
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"分片上传失败: {slice_no} - {e} (重试{max_retries}次后放弃)")
                    return False
                else:
                    logger.warning(f"分片上传失败: {slice_no} - {e} (第{attempt+1}次重试)")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            
    async def upload_complete(self, preupload_id: str) -> Dict:
        """
        完成上传
        
        Args:
            preupload_id: 预上传ID
            
        Returns:
            完成上传结果
            
        Raises:
            Pan123APIError: 完成上传失败
        """
        await self.authenticate()
        
        payload = {"preuploadID": preupload_id}
        
        data = await self._request("POST", "/upload/v2/file/upload_complete", json=payload)
        logger.debug(f"完成上传: {preupload_id} -> {data}")
        return data
        
    async def get_upload_progress(self, preupload_id: str) -> Dict:
        """
        获取上传进度（轮询）
        
        Args:
            preupload_id: 预上传ID
            
        Returns:
            上传进度信息
        """
        return await self.upload_complete(preupload_id)


class Pan123PathManager:
    """123云盘路径管理器"""
    
    def __init__(self, client: Pan123Client):
        """
        初始化路径管理器
        
        Args:
            client: 123云盘客户端实例
        """
        self.client = client
        self.path_cache: Dict[str, int] = {}  # 路径缓存: path -> folder_id
        self.path_cache["/"] = 0  # 根目录ID为0
        
    def _normalize_path(self, path: str) -> str:
        """
        标准化路径格式
        
        Args:
            path: 原始路径
            
        Returns:
            标准化后的路径
        """
        if not path or path == "/":
            return "/"
        
        # 移除首尾斜杠，替换反斜杠
        normalized = path.strip('/').replace('\\', '/')
        return f"/{normalized}"
        
    def _split_path(self, path: str) -> List[str]:
        """
        分割路径为目录名列表
        
        Args:
            path: 路径字符串
            
        Returns:
            目录名列表
        """
        normalized = self._normalize_path(path)
        if normalized == "/":
            return []
        return normalized.strip('/').split('/')
        
    async def ensure_path_exists(self, remote_path: str) -> int:
        """
        确保路径存在，返回最终目录ID
        
        Args:
            remote_path: 远程路径
            
        Returns:
            目录ID
            
        Raises:
            Pan123APIError: 创建目录失败
        """
        normalized_path = self._normalize_path(remote_path)
        
        # 检查缓存
        if normalized_path in self.path_cache:
            return self.path_cache[normalized_path]
            
        # 分割路径
        path_parts = self._split_path(normalized_path)
        if not path_parts:
            return 0  # 根目录
            
        # 递归创建路径
        current_path = ""
        parent_id = 0
        
        for part in path_parts:
            current_path = f"{current_path}/{part}" if current_path else f"/{part}"
            
            # 检查当前路径是否已缓存
            if current_path in self.path_cache:
                parent_id = self.path_cache[current_path]
                continue
                
            # 创建目录
            logger.info(f"创建目录: {current_path} (父目录ID: {parent_id})")
            folder_id = await self.client.create_folder(parent_id, part)
            
            # 缓存结果
            self.path_cache[current_path] = folder_id
            parent_id = folder_id
            
        return parent_id
        
    def clear_cache(self):
        """清空路径缓存"""
        self.path_cache.clear()
        self.path_cache["/"] = 0  # 保留根目录
        logger.info("路径缓存已清空")


def calculate_md5(file_path: str, chunk_size: int = 8192) -> str:
    """
    计算文件MD5值
    
    Args:
        file_path: 文件路径
        chunk_size: 读取块大小
        
    Returns:
        MD5哈希值
    """
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def calculate_slice_md5(data: bytes) -> str:
    """
    计算数据块MD5值
    
    Args:
        data: 二进制数据
        
    Returns:
        MD5哈希值
    """
    return hashlib.md5(data).hexdigest()