def application(environ, start_response):
    status = '200 OK'
    output = "\n".join([
	"<html>",
	"<style rel='stylesheet' type='text/css'>div, h1, table{ text-align: center; } table td { border: solid gray 1px; }</style>",
	"<title>Hello world</title>",
	"<h1>Hello world!</h1>",
	"<table align='center'>" + "\n".join(["<tr><td>{0}</td><td>{1}</td></tr>".format(key, value) for (key, value) in environ.items()]) + "</table>",
	"</html>"
    ])

    response_headers = [('Content-type', 'text/html'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]
