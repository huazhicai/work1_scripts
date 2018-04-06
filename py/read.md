## 说明文档

### new_synv.py
	note:把本地ai服务产生的在/home/recordfile下的录音tar包上到
	远端web服务的/home/recordfile下。
	
	v1.0 的assert os.popen(scp_cmd) 捕捉不到Exception , 因为popen是管道
	工作原理，shell的错误没有传过来，也就没有Exception.
	
	v1.1 把os.open() 替换为subprocess.check_call()  `check_call：执行命令，如果执行状态码是 0 ，则返回0，否则抛异常`
	如此便能捕捉到异常写入日志了。   when='D'日志并不回滚，替换为when='MIDNIGTH'， 每天凌晨就会回滚了，
	参考：https://www.cnblogs.com/qhlblog/archive/2017/12/07/7998454.html
