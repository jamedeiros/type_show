import argparse
import curses
import sys
from time import sleep


class MyCurses(object):

	def __init__(self):
		self.initialized_color = False
		self.mainwin = curses.initscr()
		self.height, self.width = self.mainwin.getmaxyx()
		self.height -= 1

		count_width = 4

		self.count_win = curses.newwin(self.height, count_width, 0, 0)
		self.data_win = curses.newwin(self.height, self.width - count_width, 0, 3)

	#B:TYPE - 1#
	def write_count(self, initial=1):
		self.count_win.clear()
		for i in range(self.height):
			self.count_win.addstr(i, 0, '{:2d}'.format(initial + i))
		self.count_win.refresh()
	#E:TYPE#

	def set_color_pair(self, idx, foreground, background):
		if not self.initialized_color:
			curses.start_color()
		curses.init_pair(idx, foreground, background)

	def move(self, x, y):
		self.data_win.move(x, y)

	def write(self, text, x=None, y=None, color=None, with_scroll=False):
		if x is not None:
			self.move(x, y)

		if with_scroll:
			self.data_win.insertln()

		if color is not None:
			self.data_win.addstr(text, curses.color_pair(color))
		else:
			self.data_win.addstr(text)
		self.data_win.refresh()

	def pause(self):
		self.data_win.getch()

	def finalize(self):
		curses.endwin()


class DelayTyping(object):
	COLOR_NORMAL    = 1
	COLOR_HIGHLIGHT = 2
	
	def __init__(self, filename, delay=None, areas=None):
		self.filename = filename
		self.delay = delay
		self.areas = list()

		self.areas_processes(areas)

		self.curses = MyCurses()
		self.curses.set_color_pair(
			idx = self.COLOR_NORMAL, 
			foreground = curses.COLOR_WHITE, 
			background = curses.COLOR_BLACK
			)
		self.curses.set_color_pair(
			idx = self.COLOR_HIGHLIGHT,
			foreground = curses.COLOR_BLACK,
			background = curses.COLOR_CYAN
		)

	def __calculate_adjusts(self, begin):
		adjust = 0
		for area in self.areas:
			if len(area) == 2:
				if begin > area[0]:
					adjust += 1
			else:
				if begin > area[1]:
					adjust += area[1] - area[0]
		return adjust

	def areas_processes(self, areas):
		aux = list()

		self.areas = list()

		for area in areas[::-1]:
			adjust = self.__calculate_adjusts(area[0])
			if len(area) == 1:
				self.areas.append([area[0], adjust])
			else:
				self.areas.append([area[0], area[1], adjust])

		self.areas = self.areas[::-1]
			
	def delayed_write(self, line, n, adjust=0):
		locate = False
		if len(line) == 0:
				self.curses.write(
					text = '',
					x = n-adjust,
					y = 0, 
					color = self.COLOR_HIGHLIGHT, 
					with_scroll = True
				)

				if self.delay is not None:
					sleep(self.delay)
		else:
			for character in line:
				if not locate:
					self.curses.write(
						text = character,
						x = n-adjust,
						y = 0, 
						color = self.COLOR_HIGHLIGHT, 
						with_scroll = True
					)
					locate = True
				else:
					self.curses.write(
						text = character,
						color = self.COLOR_HIGHLIGHT
					)

				if self.delay is not None:
					sleep(self.delay)

	def view_fixed_content(self):
		hided_lines = set()
		for area in self.areas:
			if len(area) == 2:
				hided_lines.update([area[0]])
			else:
				hided_lines.update(range(area[0], area[1] + 1))

		printed = 0

		for n, line in enumerate(self.lines, 1):
			if printed >= self.curses.height - 1:
				break

			if n in hided_lines:
				continue

			printed += 1
			self.curses.write(text=line, color=self.COLOR_NORMAL)

	def  process_file(self):
		self.lines = list()
		with open(self.filename, 'r') as fd:
			self.lines = fd.readlines()

	def view_file(self):
		self.process_file()

		self.curses.write_count()
		self.view_fixed_content()

		for area in self.areas:
			self.curses.pause()
			begin = None
			end = None
			adjust = 0

			if len(area) == 2:
				begin = end = area[0]
				adjust = area[1]
			else:
				begin = area[0]
				end = area[1]
				adjust = area[2]

			for n in range(begin - 1, end):
				self.delayed_write(self.lines[n][:-1], n, adjust)

		curses.beep()

	def show(self):
		try:
			self.view_file()
			self.curses.pause()
		except:
			pass
		finally: 
			self.curses.finalize()


def run():
	parser = argparse.ArgumentParser()
	parser.add_argument('filename', help="filename for view")
	parser.add_argument("--delay", help="typing delay when showing", type=float)
	parser.add_argument("--areas", help="areas to type, example: 10-20")
	args = parser.parse_args()

	filename = args.filename
	delay = None
	areas = list()

	if args.delay:
		delay = args.delay

	if args.areas:
		for area in args.areas.split(','):
			data = area.split('-')
			if len(data) > 1:
				areas.append([int(data[0]), int(data[1])])
			else:
				areas.append([int(data[0])])

	obj = DelayTyping(filename, delay=delay, areas=areas)
	obj.show()


if __name__ == '__main__':
	run()


