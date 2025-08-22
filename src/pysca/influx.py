# from influxdb_client import InfluxDBClient,Point
# from influxdb_client.client.write_api import SYNCHRONOUS
# _influx = InfluxDBClient(url='http://127.0.0.1:8086',org='vlinnik',token='influxdb_admin_token_2025').write_api(SYNCHRONOUS)
# p = Point('<metric>')
# for tag in ['tag','another tag']:
#     p = p.tag(tag,event.tags[tag])
# p = p.field('value',3.14)
# try:
#     _influx.write(bucket='default_bucket',record = p)
# except Exception as e:
#     pass
