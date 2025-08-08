"""123云盘集成测试"""
import asyncio
import os
import tempfile
import unittest
from unittest.mock import Mock, AsyncMock, patch
import pytest

from module.cloud_drive import CloudDrive, CloudDriveConfig
from module.pan123_client import Pan123Client, Pan123PathManager


class TestPan123Integration(unittest.TestCase):
    """123云盘集成测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.config = CloudDriveConfig(
            enable_upload_file=True,
            upload_adapter="pan123",
            remote_dir="/telegram",
            before_upload_file_zip=False,
            after_upload_file_delete=False
        )
        self.config.pan123_client_id = "test_client_id"
        self.config.pan123_client_secret = "test_client_secret"
        
        # 初始化123云盘适配器
        CloudDrive.init_upload_adapter(self.config)
        
    def tearDown(self):
        """测试后置清理"""
        if self.config.pan123_client and hasattr(self.config.pan123_client, 'session'):
            if self.config.pan123_client.session:
                asyncio.run(self.config.pan123_client._close_session())
                
    def test_init_upload_adapter(self):
        """测试上传适配器初始化"""
        self.assertIsNotNone(self.config.pan123_client)
        self.assertIsInstance(self.config.pan123_client, Pan123Client)
        self.assertIsNotNone(self.config.pan123_path_manager)
        self.assertIsInstance(self.config.pan123_path_manager, Pan123PathManager)
        
    @patch('module.pan123_client.Pan123Client')
    async def test_upload_small_file_success(self, mock_client_class):
        """测试小文件上传成功"""
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("This is a test file for 123pan upload.")
            temp_file = f.name
            
        try:
            # Mock客户端实例
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock路径管理器
            mock_path_manager = AsyncMock()
            mock_path_manager.ensure_path_exists = AsyncMock(return_value=12345)
            
            # 设置config中的mock对象
            self.config.pan123_client = mock_client
            self.config.pan123_path_manager = mock_path_manager
            
            # Mock上下文管理器
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            # Mock API调用
            mock_client.create_file = AsyncMock(return_value={
                "reuse": False,  # 不是秒传
                "preuploadID": "test_preupload_id",
                "sliceSize": 1024 * 1024,
                "servers": ["https://upload.123pan.com"]
            })
            
            mock_client.get_upload_domains = AsyncMock(return_value=[
                "https://upload.123pan.com"
            ])
            
            mock_client.upload_single = AsyncMock(return_value={
                "fileID": 54321
            })
            
            # 执行上传
            result = await CloudDrive.pan123_upload_file(
                self.config,
                "/test/save/path",
                temp_file
            )
            
            self.assertTrue(result)
            
            # 验证调用
            mock_path_manager.ensure_path_exists.assert_called_once()
            mock_client.create_file.assert_called_once()
            mock_client.get_upload_domains.assert_called_once()
            mock_client.upload_single.assert_called_once()
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
    @patch('module.pan123_client.Pan123Client')
    async def test_upload_with_instant_upload(self, mock_client_class):
        """测试秒传成功"""
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("This file will be instant uploaded.")
            temp_file = f.name
            
        try:
            # Mock客户端实例
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock路径管理器
            mock_path_manager = AsyncMock()
            mock_path_manager.ensure_path_exists = AsyncMock(return_value=12345)
            
            # 设置config中的mock对象
            self.config.pan123_client = mock_client
            self.config.pan123_path_manager = mock_path_manager
            
            # Mock上下文管理器
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            # Mock秒传响应
            mock_client.create_file = AsyncMock(return_value={
                "reuse": True,  # 秒传成功
                "fileID": 54321
            })
            
            # 执行上传
            result = await CloudDrive.pan123_upload_file(
                self.config,
                "/test/save/path",
                temp_file
            )
            
            self.assertTrue(result)
            
            # 验证调用
            mock_path_manager.ensure_path_exists.assert_called_once()
            mock_client.create_file.assert_called_once()
            
            # 秒传情况下不应该调用上传相关方法
            mock_client.get_upload_domains.assert_not_called()
            mock_client.upload_single.assert_not_called()
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
    @patch('module.pan123_client.Pan123Client')
    async def test_upload_with_compression(self, mock_client_class):
        """测试压缩上传"""
        # 启用压缩
        self.config.before_upload_file_zip = True
        
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("This file will be compressed and uploaded.")
            temp_file = f.name
            
        try:
            # Mock客户端实例
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock路径管理器
            mock_path_manager = AsyncMock()
            mock_path_manager.ensure_path_exists = AsyncMock(return_value=12345)
            
            # 设置config中的mock对象
            self.config.pan123_client = mock_client
            self.config.pan123_path_manager = mock_path_manager
            
            # Mock上下文管理器
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            # Mock秒传响应（压缩文件）
            mock_client.create_file = AsyncMock(return_value={
                "reuse": True,  # 秒传成功
                "fileID": 54321
            })
            
            # Mock zip_file方法
            with patch.object(CloudDrive, 'zip_file') as mock_zip:
                mock_zip.return_value = temp_file + ".zip"
                
                # 创建mock的zip文件
                with open(temp_file + ".zip", 'w') as zip_f:
                    zip_f.write("mock zip content")
                
                try:
                    # 执行上传
                    result = await CloudDrive.pan123_upload_file(
                        self.config,
                        "/test/save/path",
                        temp_file
                    )
                    
                    self.assertTrue(result)
                    
                    # 验证压缩方法被调用
                    mock_zip.assert_called_once_with(temp_file)
                    
                finally:
                    # 清理zip文件
                    if os.path.exists(temp_file + ".zip"):
                        os.unlink(temp_file + ".zip")
                        
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
    def test_config_compatibility(self):
        """测试配置兼容性"""
        # 测试与现有rclone配置不冲突
        rclone_config = CloudDriveConfig(
            enable_upload_file=True,
            upload_adapter="rclone",
            remote_dir="/telegram"
        )
        
        # 初始化rclone适配器不应该影响123云盘配置
        CloudDrive.init_upload_adapter(rclone_config)
        
        # rclone配置应该没有123云盘相关属性设置
        self.assertEqual(rclone_config.pan123_client_id, "")
        self.assertEqual(rclone_config.pan123_client_secret, "")
        self.assertIsNone(rclone_config.pan123_client)
        self.assertIsNone(rclone_config.pan123_path_manager)
        
    async def test_upload_file_unified_interface(self):
        """测试统一上传接口"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test unified interface.")
            temp_file = f.name
            
        try:
            # Mock 123云盘上传方法
            with patch.object(CloudDrive, 'pan123_upload_file') as mock_upload:
                mock_upload.return_value = True
                
                # 调用统一接口
                result = await CloudDrive.upload_file(
                    self.config,
                    "/test/save/path",
                    temp_file
                )
                
                self.assertTrue(result)
                mock_upload.assert_called_once_with(
                    self.config, "/test/save/path", temp_file
                )
                
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
    @patch('module.pan123_client.Pan123Client')
    async def test_upload_failure_handling(self, mock_client_class):
        """测试上传失败处理"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("This upload will fail.")
            temp_file = f.name
            
        try:
            # Mock客户端实例抛出异常
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock路径管理器
            mock_path_manager = AsyncMock()
            mock_path_manager.ensure_path_exists = AsyncMock(side_effect=Exception("Network error"))
            
            # 设置config中的mock对象
            self.config.pan123_client = mock_client
            self.config.pan123_path_manager = mock_path_manager
            
            # Mock上下文管理器
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            # 执行上传，应该返回False
            result = await CloudDrive.pan123_upload_file(
                self.config,
                "/test/save/path",
                temp_file
            )
            
            self.assertFalse(result)
            
            # 原文件应该仍然存在（失败时不删除）
            self.assertTrue(os.path.exists(temp_file))
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


# Pytest异步测试支持
@pytest.mark.asyncio
class TestPan123IntegrationAsync:
    """123云盘异步集成测试"""
    
    async def test_large_file_multipart_upload(self):
        """测试大文件分片上传"""
        # 这个测试需要mock大文件场景
        config = CloudDriveConfig(
            enable_upload_file=True,
            upload_adapter="pan123"
        )
        config.pan123_client_id = "test_id"
        config.pan123_client_secret = "test_secret"
        
        # 创建临时大文件（模拟）
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as f:
            # 写入模拟的大文件标识
            f.write(b"LARGE_FILE_MARKER" * 1000)
            temp_file = f.name
            
        try:
            # Mock文件大小检查
            with patch('os.path.getsize', return_value=2*1024*1024*1024):  # 2GB
                with patch.object(CloudDrive, '_upload_multipart_file') as mock_multipart:
                    mock_multipart.return_value = True
                    
                    # Mock其他必要的组件
                    mock_client = AsyncMock()
                    mock_path_manager = AsyncMock()
                    mock_path_manager.ensure_path_exists = AsyncMock(return_value=12345)
                    
                    config.pan123_client = mock_client
                    config.pan123_path_manager = mock_path_manager
                    
                    # Mock上下文管理器和API调用
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=None)
                    mock_client.create_file = AsyncMock(return_value={
                        "reuse": False,
                        "preuploadID": "test_preupload_id",
                        "sliceSize": 10*1024*1024,
                        "servers": ["https://upload.123pan.com"]
                    })
                    
                    # 执行上传
                    result = await CloudDrive.pan123_upload_file(
                        config, "/test", temp_file
                    )
                    
                    assert result is True
                    mock_multipart.assert_called_once()
                    
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


if __name__ == '__main__':
    # 运行同步测试
    unittest.main()