'''
Copyright (C) 2014 Terry Stewart and Travis DeWolf

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import Controllers.gc as GC

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation

class Runner:
	"""
	A class for drawing the arm simulation.

	NOTE: If you're getting an error along the lines of 
	'xrange is not an iterator', make sure that you have 
	the most recent version of matplotlib, from their github.
	"""
	def __init__(self, title='', dt=1e-4, control_steps=10, 
					   display_steps=1, t_target=1.0, 
					   seed=1, box=[-.5,.5,-.1,1], rotate=0.0,
					   control_type='', trajectory=None,
					   infinite_trail=False, mouse_control=False):
		self.dt = dt
		self.control_steps = control_steps
		self.display_steps = display_steps
		self.target_steps = int(t_target/float(dt*display_steps))
		self.trajectory = trajectory

		self.box = box 
		self.control_type = control_type 
		self.infinite_trail = infinite_trail
		self.mouse_control = mouse_control
		self.rotate = rotate
		self.title = title

		self.sim_step = 0
		self.trail_index = 0
		
	def run(self, arm, control_shell, video=None, video_time=None):
		self.arm = arm
		self.shell = control_shell
		
		fig = plt.figure(figsize=(10,10), dpi=None)
		fig.suptitle(self.title); 
		# set the padding of the subplot explicitly
		fig.subplotpars.left=.1; fig.subplotpars.right=.9
		fig.subplotpars.bottom=.1; fig.subplotpars.top=.9

		ax = fig.add_subplot(1, 1, 1, 
							 xlim=(self.box[0], self.box[1]), 
							 ylim=(self.box[2], self.box[3]))
		# ax.xaxis.grid(); ax.yaxis.grid()
		# make it a square plot
		ax.set_aspect('equal') 

		# set up plot elements
		self.trail, = ax.plot([], [], color='#888888', lw=8)
		self.arm_line, = ax.plot([], [], 'o-', mew=8, color='r', lw=6)
		self.target_line, = ax.plot([], [], 'r-x', mew=4)
		self.info = ax.text(self.box[0]+abs(.1*self.box[0]), \
							self.box[3]-abs(.1*self.box[3]), \
							'', va='top')
		self.trail_data = np.ones((self.target_steps, 2), \
								   dtype='float') * np.NAN	

		if self.trajectory is not None:
			ax.plot(self.trajectory[:,0], self.trajectory[:,1], alpha=.3)

		# connect up mouse event if specified
		if self.mouse_control: 
			self.target = self.shell.controller.gen_target(arm)
			# get pixel width of fig (-.2 for the padding)
			self.fig_width = (fig.get_figwidth() - .2 \
								* fig.get_figwidth()) * fig.get_dpi()
			def move_target(event): 
				# get mouse position and scale appropriately to convert to (x,y) 
				target = ((np.array([event.x, event.y]) - .5 * fig.get_dpi()) /\
								self.fig_width) * \
								(self.box[1] - self.box[0]) + self.box[0]

				# set target for the controller
				self.target = \
					self.shell.controller.set_target_from_mouse(target)

			# hook up function to mouse event
			fig.canvas.mpl_connect('motion_notify_event', move_target)

		if video_time is None:
			frames = 50
		else:
			frames = int(video_time/(self.dt*self.display_steps))

		anim = animation.FuncAnimation(fig, self.anim_animate, 
				   init_func=self.anim_init, frames=50, interval=0, blit=True)
		
		if video is not None:
			anim.save(video, fps=1.0/(self.dt*self.display_steps), dpi=200)
		
		self.anim = anim

	def make_info_text(self):
		text = []
		text.append('t = %1.4g'%(self.sim_step*self.dt)) #
		u_text = ' '.join('%4.3f,'%F for F in self.shell.u)
		text.append('u = ['+u_text+']')

		if self.control_type.startswith('adaptive'):
			theta_text = ' '.join('%4.3f,'%F for F in self.control.theta)
			text.append('theta = ['+theta_text+']')
				
		return '\n'.join(text)    

	def anim_init(self):
		self.info.set_text('')
		self.arm_line.set_data([], [])
		self.target_line.set_data([], [])
		self.trail.set_data([], [])
		return self.arm_line, self.target_line, self.trail

	def anim_animate(self, i):

		if self.control_type == 'random':
			# update target after specified period of time passes
			if self.sim_step % (self.target_steps*self.display_steps) == 0:
				self.target = self.shell.controller.gen_target(self.arm)
		else:
			self.target = self.shell.controller.target
	   
		# before drawing
		for j in range(self.display_steps):            
			# update control signal
			if self.sim_step % self.control_steps == 0 or \
				'tau' not in locals():
					tau = self.shell.control(self.arm)
			# apply control signal and simulate
			self.arm.apply_torque(u=tau, dt=self.dt)
	
			self.sim_step +=1
		
		# update figure
		self.arm_line.set_data(*self.arm.position(rotate=self.rotate))
		# self.info.set_text(self.make_info_text())
		self.trail.set_data(self.trail_data[:,0], self.trail_data[:,1])
		if self.target is not None:
			if isinstance(self.shell.controller, GC.Control):
				# convert to plottable form if necessary
				target = self.arm.position(q=self.target, rotate=self.rotate)
			else:
				target = self.target
			self.target_line.set_data(target)
			
		# update hand trail
		if self.shell.pen_down:
			if self.infinite_trail:
				# if we're writing, keep all pen_down history
				self.trail_index += 1

				# if we've hit the end of the trail, double it and copy
				if self.trail_index >= self.trail_data.shape[0]-1:
					trail_data = np.zeros((self.trail_data.shape[0]*2,
										   self.trail_data.shape[1]))*np.nan
					trail_data[:self.trail_index+1] = self.trail_data
					self.trail_data = trail_data

				self.trail_data[self.trail_index] = \
										self.arm_line.get_xydata()[-1]
			else:
				# else just use a buffer window
				self.trail_data[:-1] = self.trail_data[1:]
				self.trail_data[-1] = self.arm_line.get_xydata()[-1]
		else: 
			# if pen up add a break in the trail
			self.trail_data[self.trail_index] = [np.nan, np.nan]

		return self.target_line, self.info, self.trail, self.arm_line

	def show(self):
		try:
			plt.show()
		except AttributeError:
			pass
