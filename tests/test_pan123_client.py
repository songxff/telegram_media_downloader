"""123云盘客户端单元测试"""
import asyncio
import os
import tempfile
import unittest
from unittest.mock import Mock, AsyncMock, patch
import pytest

from module.pan123_client import (
    Pan123Client, 
    Pan123PathManager, 
    Pan123AuthError, 
    Pan123APIError,
    calculate_md5,
    calculate_slice_md5
)


class TestPan123Client(unittest.TestCase):
    """Pan123Client单元测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.client = Pan123Client("test_client_id", "test_client_secret")
        
    def tearDown(self):
        """测试后置清理"""
        # 确保会话被关闭
        if hasattr(self.client, 'session') and self.client.session:
            asyncio.run(self.client._close_session())
            
    def test_client_init(self):
        """测试客户端初始化"""
        self.assertEqual(self.client.client_id, "test_client_id")
        self.assertEqual(self.client.client_secret, "test_client_secret")
        self.assertEqual(self.client.base_url, "https://open-api.123pan.com")
        self.assertIsNone(self.client.access_token)
        
    def test_get_common_headers(self):
        """测试获取通用请求头"""
        headers = self.client._get_common_headers()
        self.assertEqual(headers["Platform"], "open_platform")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertNotIn("Authorization", headers)
        
        # 设置access_token后测试
        self.client.access_token = "test_token"
        headers = self.client._get_common_headers()
        self.assertEqual(headers["Authorization"], "Bearer test_token")
        
    def test_is_token_expired(self):
        """测试token过期检查"""
        from datetime import datetime, timedelta
        
        # 无过期时间，应该过期
        self.assertTrue(self.client._is_token_expired())
        
        # 未过期的token
        self.client.token_expires_at = datetime.now() + timedelta(hours=1)
        self.assertFalse(self.client._is_token_expired())
        
        # 已过期的token
        self.client.token_expires_at = datetime.now() - timedelta(hours=1)
        self.assertTrue(self.client._is_token_expired())
        
    @patch('httpx.AsyncClient')
    async def test_authenticate_success(self, mock_client):
        """测试认证成功"""
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "accessToken": "test_access_token",
                "expiredAt": "2024-12-31T23:59:59Z"
            }
        }
        
        mock_session = AsyncMock()
        mock_session.request.return_value = mock_response
        mock_client.return_value = mock_session
        self.client.session = mock_session
        
        token = await self.client.authenticate()
        
        self.assertEqual(token, "test_access_token")
        self.assertEqual(self.client.access_token, "test_access_token")
        self.assertIsNotNone(self.client.token_expires_at)
        
    @patch('httpx.AsyncClient')
    async def test_authenticate_failure(self, mock_client):
        """测试认证失败"""
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "code": 401,
            "message": "Invalid credentials"
        }
        
        mock_session = AsyncMock()
        mock_session.request.return_value = mock_response
        mock_client.return_value = mock_session
        self.client.session = mock_session
        
        with self.assertRaises(Pan123AuthError):
            await self.client.authenticate()
            
    @patch('httpx.AsyncClient')
    async def test_get_upload_domains(self, mock_client):
        """测试获取上传域名"""
        # Mock认证
        self.client.access_token = "test_token"
        self.client.token_expires_at = None  # 强制过期来测试认证
        
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "servers": ["https://upload1.123pan.com", "https://upload2.123pan.com"]
            }
        }
        
        mock_session = AsyncMock()
        mock_session.request.return_value = mock_response
        mock_client.return_value = mock_session
        self.client.session = mock_session
        
        # Mock authenticate方法
        self.client.authenticate = AsyncMock(return_value="test_token")
        
        domains = await self.client.get_upload_domains()
        
        self.assertEqual(len(domains), 2)
        self.assertIn("https://upload1.123pan.com", domains)
        self.assertIn("https://upload2.123pan.com", domains)
        
    @patch('httpx.AsyncClient')
    async def test_create_folder(self, mock_client):
        """测试创建文件夹"""
        # Mock认证
        self.client.authenticate = AsyncMock(return_value="test_token")
        
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "dirID": 12345
            }
        }
        
        mock_session = AsyncMock()
        mock_session.request.return_value = mock_response
        mock_client.return_value = mock_session
        self.client.session = mock_session
        
        folder_id = await self.client.create_folder(0, "test_folder")
        
        self.assertEqual(folder_id, 12345)
        
    def test_calculate_md5(self):
        """测试MD5计算"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Hello, World!")
            temp_file = f.name
            
        try:
            md5_hash = calculate_md5(temp_file)
            # "Hello, World!" 的MD5值
            expected_md5 = "65a8e27d8879283831b664bd8b7f0ad4"
            self.assertEqual(md5_hash, expected_md5)
        finally:
            os.unlink(temp_file)
            
    def test_calculate_slice_md5(self):
        """测试分片MD5计算"""
        data = b"Hello, World!"
        md5_hash = calculate_slice_md5(data)
        expected_md5 = "65a8e27d8879283831b664bd8b7f0ad4"
        self.assertEqual(md5_hash, expected_md5)


class TestPan123PathManager(unittest.TestCase):
    """Pan123PathManager单元测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.client = Mock()
        self.path_manager = Pan123PathManager(self.client)
        
    def test_normalize_path(self):
        """测试路径标准化"""
        test_cases = [
            ("", "/"),
            ("/", "/"),
            ("test", "/test"),
            ("/test/", "/test"),
            ("test/folder", "/test/folder"),
            ("\\test\\folder\\", "/test/folder"),
            ("test\\folder/subfolder", "/test/folder/subfolder")
        ]
        
        for input_path, expected in test_cases:
            result = self.path_manager._normalize_path(input_path)
            self.assertEqual(result, expected, f"Failed for input: {input_path}")
            
    def test_split_path(self):
        """测试路径分割"""
        test_cases = [
            ("/", []),
            ("/test", ["test"]),
            ("/test/folder", ["test", "folder"]),
            ("/test/folder/subfolder", ["test", "folder", "subfolder"])
        ]
        
        for input_path, expected in test_cases:
            result = self.path_manager._split_path(input_path)
            self.assertEqual(result, expected, f"Failed for input: {input_path}")
            
    async def test_ensure_path_exists_cached(self):
        """测试路径存在检查（缓存命中）"""
        # 预设缓存
        self.path_manager.path_cache["/test/folder"] = 12345
        
        result = await self.path_manager.ensure_path_exists("/test/folder")
        
        self.assertEqual(result, 12345)
        # 不应该调用客户端的create_folder方法
        self.client.create_folder.assert_not_called()
        
    async def test_ensure_path_exists_create_new(self):
        """测试路径存在检查（创建新路径）"""
        # Mock客户端的create_folder方法
        self.client.create_folder = AsyncMock(side_effect=[111, 222, 333])
        
        result = await self.path_manager.ensure_path_exists("/test/folder/subfolder")
        
        # 应该创建3个文件夹
        self.assertEqual(self.client.create_folder.call_count, 3)
        self.assertEqual(result, 333)
        
        # 检查缓存
        self.assertEqual(self.path_manager.path_cache["/test"], 111)
        self.assertEqual(self.path_manager.path_cache["/test/folder"], 222)
        self.assertEqual(self.path_manager.path_cache["/test/folder/subfolder"], 333)
        
    def test_clear_cache(self):
        """测试清空缓存"""
        # 添加一些缓存项
        self.path_manager.path_cache["/test"] = 123
        self.path_manager.path_cache["/test/folder"] = 456
        
        self.path_manager.clear_cache()
        
        # 只保留根目录
        self.assertEqual(len(self.path_manager.path_cache), 1)
        self.assertEqual(self.path_manager.path_cache["/"], 0)


# Pytest异步测试支持
@pytest.mark.asyncio
class TestPan123ClientAsync:
    """Pan123Client异步测试"""
    
    async def test_context_manager(self):
        """测试异步上下文管理器"""
        client = Pan123Client("test_id", "test_secret")
        
        async with client:
            self.assertIsNotNone(client.session)
            
        # 退出后session应该被关闭
        self.assertIsNone(client.session)


if __name__ == '__main__':
    # 运行同步测试
    unittest.main()