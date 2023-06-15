import ftplib
import os

    
###FTP上传####
def ftp_upload(f,file_remote,file_local,show=1):#FTP文件二进制传输
    bufsize = 1024  # 设置缓冲器大小
    with open(file_local, 'rb') as fp:
        f.storbinary('STOR ' + file_remote, fp, bufsize)
        if show:
            print("From: ",file_local)
            print("To  : ",file_remote)
            print("Upload successful!!! ")
        fp.close()    
    return()

def ftp_download(f,file_remote,file_local,show=1):#FTP文件二进制传输
    bufsize = 1024  # 设置缓冲器大小
    file_path = os.path.split(file_local)[0]
    if not os.path.exists(file_path) : os.makedirs(file_path)
    with open(file_local, 'wb') as fp:
        try:
            f.retrbinary('RETR ' + file_remote, fp.write, bufsize)
            if show:
                print("From: ",file_remote)
                print("To  : ",file_local)
                print("Download successful!!! ")
        except Exception as data:
            print("File_Download_ERROR: {0}:  {1}".format(file_local,data))
        # finally:
        fp.close()    
        return()
        

def ftp_trans(ftp_host,local_list,ftp_list,remove=False,replace=False,
                method=None, is_show=False, **kargs):
    """
    #remove:是否删除原文件，replace:是否替代目标文件
    method: mc.BF.ftp_upload为上传；mc.BF.ftp_download为下载
    """    
    if method is None: 
        method = ftp_upload

    f = ftplib.FTP()  # 实例化FTP对象
    f.connect(ftp_host[0],ftp_host[1])#ip，端口
    f.login(ftp_host[2],ftp_host[3])
    if is_show: f.set_debuglevel(2)
    f.set_pasv(True)#被动模式传输
#       f.dir()#显示ftp目录
    for i,local_file in enumerate(local_list):
        ftp_file = ftp_list[i]
        ftp_dir = os.path.split(ftp_file)[0]
#            print(ftp_dir)
        try:
            f.cwd(ftp_dir)
        except ftplib.error_perm:
            print(ftp_dir)
            f.mkd(ftp_dir)
        if replace==True:
            ftp_file_list = f.nlst(ftp_dir)
            if ftp_file in ftp_file_list: continue#原目录中有上传文件名，则不进行上传
        method(f,ftp_file,local_file,show=1)
        if remove:os.remove(local_file)
    f.quit()
    return()



###SFTP上传/下载####
def sftp_trans(sftp_host,local_list,sftp_list,method="put", remove=False):
    import paramiko
    client = paramiko.Transport( (sftp_host[0],sftp_host[1]) )
    client.connect( username=sftp_host[2],password=sftp_host[3] )
    sftp = paramiko.SFTPClient.from_transport(client)
    for i,local_file in enumerate(local_list):
        sftp_file = sftp_list[i]
        sftp_dir = os.path.split(sftp_file)[0]
        try:
            sftp.chdir(sftp_dir)
        except Exception:
            sftp.mkdir(sftp_dir)
            sftp.chdir(sftp_dir)
        finally:
            if method == "put":
                sftp.put(local_file, sftp_file)
            elif method == "get":
                sftp.get(local_file, sftp_file)
        if remove:os.remove(local_file)
    print("SFTP Success!")
    sftp.close()
    client.close()
    return()