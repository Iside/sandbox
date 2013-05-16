[program:nginx]
command=nginx -c {{ supervisor_dir }}/nginx.conf
directory=/
stdout_logfile={{ supervisor_dir }}/nginx_access.log
stderr_logfile={{ supervisor_dir }}/nginx_error.log

{# vim: set ft=jinja: #}
