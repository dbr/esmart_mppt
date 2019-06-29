#!/usr/bin/python3
# -*- coding: utf-8 -*-

import esmart
import time
import influxdb


class InfluxLogger(object):
	def __init__(self):
		self.connection = influxdb.InfluxDBClient(database='solar')

	def handle_data(self, d: esmart.SolarData):
		# Correct error in readings
		#d['bat_volt'] *= 1.107
		#d['load_volt'] *= 1.09
		# Only correct if reading is not zero
		#if d['chg_cur']:
		#	d['chg_cur'] += 1.5

		# chg_power uses uncorrected voltage/current, so recalculate
		#actual_power = d['bat_volt']*d['chg_cur']

		print("PV %.1f V, battery %.1f V" % (d.pv_volt, d.bat_volt))
		print("Charging %s, %.1f A, %.1f W" % (esmart.DEVICE_MODE[d.chg_mode], d.chg_cur, d.bat_volt * d.chg_power))
		print("Discharging %.1f V, %.1f A, %.1f W" % (d.load_volt, d.load_cur, d.load_power))

		datadict = {
			'bat_volt': d.bat_volt,
			'bat_temp': d.bat_temp,
			'chg_mode': esmart.DEVICE_MODE[d.chg_mode],
			'chg_power': d.chg_power,
			'pv_volt': d.pv_volt,
			'chg_cur': d.chg_cur,
			'load_volt': d.load_volt,
			'load_cur': d.load_cur,
			'load_power': d.load_power,
			'int_temp': d.int_temp,
			'soc': d.soc,
			}


		points = []

		timestamp = time.ctime()
		points.append({
			'time': timestamp,
			'measurement': 'van_scc',
			'fields': datadict,
		})
		print(points)
		self.connection.write_points(points)



def main():
	ifd = InfluxLogger()
	e = esmart.Esmart()
	e.open("/dev/ttyUSB0")
	e.set_callback(ifd.handle_data)

	while True:
		e.tick()
		time.sleep(0.05)


if __name__ == "__main__":
	main()
