## 说明文档

### new_synv.py
	note:把本地ai服务产生的在/home/recordfile下的录音tar包上到
	远端web服务的/home/recordfile下。
	
	v1.0 的assert os.popen(scp_cmd) 捕捉不到Exception , 因为popen是管道
	工作原理，shell的错误没有传过来，也就没有Exception.
	
