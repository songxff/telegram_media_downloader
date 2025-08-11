"""provide upload cloud drive"""
import asyncio
import functools
import importlib
import inspect
import os
import re
from asyncio import subprocess
from subprocess import Popen
from typing import Callable
from zipfile import ZipFile

from loguru import logger

from utils import platform


# pylint: disable = R0902
class CloudDriveConfig:
    """Rclone Config"""

    def __init__(
        self,
        enable_upload_file: bool = False,
        before_upload_file_zip: bool = False,
        after_upload_file_delete: bool = True,
        rclone_path: str = os.path.join(
            os.path.abspath("."), "rclone", f"rclone{platform.get_exe_ext()}"
        ),
        remote_dir: str = "",
        upload_adapter: str = "rclone",
    ):
        self.enable_upload_file = enable_upload_file
        self.before_upload_file_zip = before_upload_file_zip
        self.after_upload_file_delete = after_upload_file_delete
        self.rclone_path = rclone_path
        self.remote_dir = remote_dir
        self.upload_adapter = upload_adapter
        self.dir_cache: dict = {}  # for remote mkdir
        self.total_upload_success_file_count = 0
        self.aligo = None
        
        # 123云盘配置
        self.pan123_client_id: str = ""
        self.pan123_client_secret: str = ""
        self.pan123_client = None
        self.pan123_path_manager = None

    def pre_run(self):
        """pre run init upload adapter"""
        if self.enable_upload_file:
            CloudDrive.init_upload_adapter(self)


class CloudDrive:
    """rclone support"""

    @staticmethod
    def init_upload_adapter(drive_config: CloudDriveConfig):
        """Initialize the upload adapter."""
        if drive_config.upload_adapter == "aligo":
            Aligo = importlib.import_module("aligo").Aligo
            drive_config.aligo = Aligo()
        elif drive_config.upload_adapter == "pan123":
            from module.pan123_client import Pan123Client, Pan123PathManager
            if not drive_config.pan123_client_id or not drive_config.pan123_client_secret:
                logger.error("123云盘配置错误: client_id和client_secret不能为空")
                return
            drive_config.pan123_client = Pan123Client(
                drive_config.pan123_client_id,
                drive_config.pan123_client_secret
            )
            drive_config.pan123_path_manager = Pan123PathManager(
                drive_config.pan123_client
            )

    @staticmethod
    def rclone_mkdir(drive_config: CloudDriveConfig, remote_dir: str):
        """mkdir in remote"""
        with Popen(
            f'"{drive_config.rclone_path}" mkdir "{remote_dir}/"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ):
            pass

    @staticmethod
    def aligo_mkdir(drive_config: CloudDriveConfig, remote_dir: str):
        """mkdir in remote by aligo"""
        if drive_config.aligo and not drive_config.aligo.get_folder_by_path(remote_dir):
            drive_config.aligo.create_folder(name=remote_dir, check_name_mode="refuse")

    @staticmethod
    def zip_file(local_file_path: str) -> str:
        """
        Zip local file
        """

        file_path_without_extension = os.path.splitext(local_file_path)[0]
        zip_file_name = file_path_without_extension + ".zip"

        with ZipFile(zip_file_name, "w") as zip_writer:
            zip_writer.write(local_file_path)

        return zip_file_name

    # pylint: disable = R0914
    @staticmethod
    async def rclone_upload_file(
        drive_config: CloudDriveConfig,
        save_path: str,
        local_file_path: str,
        progress_callback: Callable = None,
        progress_args: tuple = (),
    ) -> bool:
        """Use Rclone upload file"""
        upload_status: bool = False
        try:
            remote_dir = (
                drive_config.remote_dir
                + "/"
                + os.path.dirname(local_file_path).replace(save_path, "")
                + "/"
            ).replace("\\", "/")

            if not drive_config.dir_cache.get(remote_dir):
                CloudDrive.rclone_mkdir(drive_config, remote_dir)
                drive_config.dir_cache[remote_dir] = True

            zip_file_path: str = ""
            file_path = local_file_path
            if drive_config.before_upload_file_zip:
                zip_file_path = CloudDrive.zip_file(local_file_path)
                file_path = zip_file_path
            else:
                file_path = local_file_path

            cmd = (
                f'"{drive_config.rclone_path}" copy "{file_path}" '
                f'"{remote_dir}/" --create-empty-src-dirs --ignore-existing --progress'
            )
            proc = await asyncio.create_subprocess_shell(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            if proc.stdout:
                async for output in proc.stdout:
                    s = output.decode(errors="replace")
                    print(s)
                    if "Transferred" in s and "100%" in s and "1 / 1" in s:
                        logger.info(f"upload file {local_file_path} success")
                        drive_config.total_upload_success_file_count += 1
                        if drive_config.after_upload_file_delete:
                            os.remove(local_file_path)
                        if drive_config.before_upload_file_zip:
                            os.remove(zip_file_path)
                        upload_status = True
                    else:
                        pattern = (
                            r"Transferred: (.*?) / (.*?), (.*?)%, (.*?/s)?, ETA (.*?)$"
                        )
                        transferred_match = re.search(pattern, s)

                        if transferred_match:
                            if progress_callback:
                                func = functools.partial(
                                    progress_callback,
                                    transferred_match.group(1),
                                    transferred_match.group(2),
                                    transferred_match.group(3),
                                    transferred_match.group(4),
                                    transferred_match.group(5),
                                    *progress_args,
                                )

                            if inspect.iscoroutinefunction(progress_callback):
                                await func()

            await proc.wait()
        except Exception as e:
            logger.error(f"{e.__class__} {e}")
            return False

        return upload_status

    @staticmethod
    def aligo_upload_file(
        drive_config: CloudDriveConfig, save_path: str, local_file_path: str
    ):
        """aliyun upload file"""
        upload_status: bool = False
        if not drive_config.aligo:
            logger.warning("please config aligo! see README.md")
            return False

        try:
            remote_dir = (
                drive_config.remote_dir
                + "/"
                + os.path.dirname(local_file_path).replace(save_path, "")
                + "/"
            ).replace("\\", "/")

            if not drive_config.dir_cache.get(remote_dir):
                CloudDrive.aligo_mkdir(drive_config, remote_dir)
                aligo_dir = drive_config.aligo.get_folder_by_path(remote_dir)
                if aligo_dir:
                    drive_config.dir_cache[remote_dir] = aligo_dir.file_id

            zip_file_path: str = ""
            file_paths = []
            if drive_config.before_upload_file_zip:
                zip_file_path = CloudDrive.zip_file(local_file_path)
                file_paths.append(zip_file_path)
            else:
                file_paths.append(local_file_path)

            res = drive_config.aligo.upload_files(
                file_paths=file_paths,
                parent_file_id=drive_config.dir_cache[remote_dir],
                check_name_mode="refuse",
            )

            if len(res) > 0:
                drive_config.total_upload_success_file_count += len(res)
                if drive_config.after_upload_file_delete:
                    os.remove(local_file_path)

                if drive_config.before_upload_file_zip:
                    os.remove(zip_file_path)

                upload_status = True

        except Exception as e:
            logger.error(f"{e.__class__} {e}")
            return False

        return upload_status

    @staticmethod
    async def upload_file(
        drive_config: CloudDriveConfig, save_path: str, local_file_path: str
    ) -> bool:
        """Upload file
        Parameters
        ----------
        drive_config: CloudDriveConfig
            see @CloudDriveConfig

        save_path: str
            Local file save path config

        local_file_path: str
            Local file path

        Returns
        -------
        bool
            True or False
        """
        if not drive_config.enable_upload_file:
            return False

        ret: bool = False
        if drive_config.upload_adapter == "rclone":
            ret = await CloudDrive.rclone_upload_file(
                drive_config, save_path, local_file_path
            )
        elif drive_config.upload_adapter == "aligo":
            ret = CloudDrive.aligo_upload_file(drive_config, save_path, local_file_path)
        elif drive_config.upload_adapter == "pan123":
            ret = await CloudDrive.pan123_upload_file(
                drive_config, save_path, local_file_path
            )

        return ret

    @staticmethod
    async def pan123_upload_file(
        drive_config: CloudDriveConfig,
        save_path: str,
        local_file_path: str,
        progress_callback: Callable = None,
        progress_args: tuple = ()
    ) -> bool:
        """
        123云盘上传文件
        
        Args:
            drive_config: 云盘配置
            save_path: 本地保存路径
            local_file_path: 本地文件路径
            progress_callback: 进度回调函数
            progress_args: 进度回调参数
            
        Returns:
            上传是否成功
        """
        from module.pan123_client import calculate_md5
        
        upload_status = False
        zip_file_path = ""
        
        if not drive_config.pan123_client:
            logger.error("123云盘客户端未初始化")
            return False
            
        try:
            # 1. 处理文件压缩
            file_path = local_file_path
            if drive_config.before_upload_file_zip:
                zip_file_path = CloudDrive.zip_file(local_file_path)
                file_path = zip_file_path
                
            # 2. 计算远程路径（基于原始文件路径，不是压缩后的）
            relative_dir = os.path.dirname(local_file_path).replace(save_path, "")
            remote_path = (drive_config.remote_dir + "/" +
                          relative_dir.replace("\\", "/")).replace("//", "/")
            
            # 3&4&5. 在一个上下文管理器中处理所有API调用
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            file_md5 = calculate_md5(file_path)
            
            logger.info(f"准备上传文件到123云盘: {file_name} (大小: {file_size} bytes)")
            
            async with drive_config.pan123_client:
                # 确保远程目录存在
                parent_id = await drive_config.pan123_path_manager.ensure_path_exists(remote_path)
                
                # 创建文件（检测秒传）
                create_result = await drive_config.pan123_client.create_file(
                    parent_id=parent_id,
                    filename=file_name,
                    etag=file_md5,
                    size=file_size
                )
                
                # 6. 处理秒传
                if create_result.get("reuse"):
                    logger.info(f"123云盘秒传成功: {file_name}")
                    upload_status = True
                else:
                    # 7. 选择上传策略
                    if file_size < 1024 * 1024 * 1024:  # <1GB 单步上传
                        upload_status = await CloudDrive._upload_single_file_internal(
                            drive_config.pan123_client, file_path, parent_id, file_name, 
                            file_md5, file_size, progress_callback, progress_args
                        )
                    else:  # ≥1GB 分片上传
                        upload_status = await CloudDrive._upload_multipart_file_internal(
                            drive_config.pan123_client, file_path, create_result, file_name,
                            progress_callback, progress_args
                        )
                        
            # 8. 上传后处理
            if upload_status:
                drive_config.total_upload_success_file_count += 1
                if drive_config.after_upload_file_delete:
                    os.remove(local_file_path)
                    logger.info(f"删除本地文件: {local_file_path}")
                if zip_file_path and drive_config.before_upload_file_zip:
                    os.remove(zip_file_path)
                    logger.info(f"删除压缩文件: {zip_file_path}")
                logger.info(f"123云盘上传成功: {local_file_path}")
            else:
                logger.error(f"123云盘上传失败: {local_file_path}")
                
        except Exception as e:
            logger.error(f"123云盘上传异常: {e}")
            upload_status = False
            
        return upload_status
        
    @staticmethod
    async def _upload_single_file_internal(
        client,
        file_path: str,
        parent_id: int,
        file_name: str,
        file_md5: str,
        file_size: int,
        progress_callback: Callable = None,
        progress_args: tuple = ()
    ) -> bool:
        """单步上传文件（内部方法，假设已在上下文中）"""
        try:
            # 获取上传域名
            upload_domains = await client.get_upload_domains()
            if not upload_domains:
                logger.error("无法获取上传域名")
                return False
                
            upload_domain = upload_domains[0]  # 选择第一个域名
            logger.info(f"使用上传域名: {upload_domain}")
            
            # 执行单步上传
            result = await client.upload_single(
                upload_domain=upload_domain,
                file_path=file_path,
                parent_id=parent_id,
                filename=file_name,
                etag=file_md5,
                size=file_size
            )
            
            return result.get("fileID") is not None
            
        except Exception as e:
            logger.error(f"单步上传失败: {e}")
            return False
            
    @staticmethod
    async def _upload_multipart_file_internal(
        client,
        file_path: str,
        create_result: dict,
        file_name: str,
        progress_callback: Callable = None,
        progress_args: tuple = ()
    ) -> bool:
        """分片上传文件（内部方法，假设已在上下文中）"""
        from module.pan123_client import calculate_slice_md5
        
        try:
            preupload_id = create_result["preuploadID"]
            slice_size = create_result["sliceSize"]
            upload_domains = create_result["servers"]
            
            if not upload_domains:
                logger.error("创建文件响应中无上传域名")
                return False
                
            upload_domain = upload_domains[0]
            total_size = os.path.getsize(file_path)
            uploaded_size = 0
            slice_no = 1
            
            logger.info(f"开始分片上传: {file_name} (分片大小: {slice_size})")
            
            # 分片上传
            with open(file_path, 'rb') as f:
                while True:
                    slice_data = f.read(slice_size)
                    if not slice_data:
                        break
                        
                    # 计算分片MD5
                    slice_md5 = calculate_slice_md5(slice_data)
                    
                    # 上传分片
                    success = await client.upload_slice(
                        upload_domain=upload_domain,
                        preupload_id=preupload_id,
                        slice_no=slice_no,
                        slice_data=slice_data,
                        slice_md5=slice_md5
                    )
                    
                    if not success:
                        logger.error(f"分片 {slice_no} 上传失败")
                        return False
                        
                    # 更新进度
                    uploaded_size += len(slice_data)
                    progress_percent = (uploaded_size / total_size) * 100
                    
                    if progress_callback:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(
                                uploaded_size, total_size, f"{progress_percent:.1f}%",
                                *progress_args
                            )
                        else:
                            progress_callback(
                                uploaded_size, total_size, f"{progress_percent:.1f}%",
                                *progress_args
                            )
                            
                    logger.debug(f"分片 {slice_no} 上传完成 ({progress_percent:.1f}%)")
                    slice_no += 1
                    
            # 完成上传
            complete_result = await client.upload_complete(preupload_id)
                
            # 如果未完成，轮询等待
            max_retries = 60  # 最多等待60秒
            retry_count = 0
            
            while not complete_result.get("completed") and retry_count < max_retries:
                logger.info("等待上传完成...")
                await asyncio.sleep(1)
                complete_result = await client.get_upload_progress(preupload_id)
                retry_count += 1
                
            success = complete_result.get("completed", False) and complete_result.get("fileID") is not None
            
            if success:
                logger.info(f"分片上传完成: {file_name}")
            else:
                logger.error(f"分片上传最终失败: {file_name}")
                
            return success
            
        except Exception as e:
            logger.error(f"分片上传异常: {e}")
            return False
