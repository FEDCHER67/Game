"""Ideal trailing-caster kinematics. Blender +Z up, +Y heading, +X axle."""
import math
RADIUS=.105
TRAIL=.035
def rotate(x,y,a):
    c,s=math.cos(a),math.sin(a)
    return c*x-s*y,s*x+c*y
def smooth(u):
    u=max(0,min(1,u));return u*u*(3-2*u)
def pose(t):
    if t<3:return 0,1.1*smooth(t/3),0,'forward'
    if t<6:
        a=math.pi*.5*smooth((t-3)/3)
        return -(1-math.cos(a)),1.1+math.sin(a),a,'turn'
    if t<7:return -1,2.1,math.pi*.5,'pause'
    if t<11:return -1+1.1*smooth((t-7)/4),2.1,math.pi*.5,'reverse'
    if t<14:return .1,2.1-.85*smooth((t-11)/3),math.pi*.5,'sideways'
    if t<17:return .1,1.25,math.pi*.5+math.pi*.5*smooth((t-14)/3),'pivot_turn'
    return .1,1.25,math.pi,'stop'
def integrate(theta,spin,vx,vy,dt,seed_sign=1):
    speed=math.hypot(vx,vy)
    count=max(1,math.ceil(speed*dt/(TRAIL*.05)))
    h=dt/count;seeded=False
    for _ in range(count):
        longitudinal=-vx*math.sin(theta)+vy*math.cos(theta)
        lateral=-vx*math.cos(theta)-vy*math.sin(theta)
        if longitudinal < -1e-5 and abs(lateral)<speed*1e-5:
            # A 0.5-degree mechanical imperfection breaks ideal reverse symmetry.
            theta+=seed_sign*math.radians(.5);seeded=True
        rate0=(-vx*math.cos(theta)-vy*math.sin(theta))/TRAIL
        mid=theta+.5*h*rate0
        rate=(-vx*math.cos(mid)-vy*math.sin(mid))/TRAIL
        signed_speed=-vx*math.sin(mid)+vy*math.cos(mid)
        theta+=h*rate
        spin-=signed_speed*h/RADIUS
    return theta,spin,seeded
def simulate(anchors,fps=24,duration=18):
    state={name:{'heading':0.,'spin':0.} for name in anchors}
    rows=[];seeds=[]
    for frame in range(1,int(duration*fps)+1):
        t=(frame-1)/fps;px,py,yaw,phase=pose(t)
        if frame>1:
            t0=t-1/fps;steps=max(10,math.ceil(abs(yaw-pose(t0)[2])/.01));dt=1/fps/steps
            for step in range(steps):
                a=pose(t0+step*dt);b=pose(t0+(step+1)*dt)
                for name,(ax,ay) in anchors.items():
                    ap=rotate(ax,ay,a[2]);bp=rotate(ax,ay,b[2])
                    vx=((b[0]+bp[0])-(a[0]+ap[0]))/dt
                    vy=((b[1]+bp[1])-(a[1]+ap[1]))/dt
                    s=state[name]
                    s['heading'],s['spin'],seeded=integrate(s['heading'],s['spin'],vx,vy,dt,-1 if 'Left' in name else 1)
                    if seeded:seeds.append({'frame':frame,'wheel':name})
        rows.append({'frame':frame,'time_s':t,'phase':phase,'root':[px,py,yaw],
            'wheels':{name:{'world_heading':s['heading'],'steer':s['heading']-yaw,'spin':s['spin']} for name,s in state.items()}})
    return rows,seeds
def validate():
    theta,spin,_=integrate(0,0,0,1,1)
    assert abs(theta)<1e-12 and abs(spin+1/RADIUS)<1e-8
    th1,sp1,_=integrate(.7,0,0,.5,2);th2,sp2,_=integrate(.7,0,0,1,1)
    assert abs(th1-th2)<1e-9 and abs(sp1-sp2)<1e-9
    th3,sp3,_=integrate(th2,sp2,0,0,1)
    assert th3==th2 and sp3==sp2
    th4,sp4,_=integrate(0,0,0,-.2,4)
    reverse_error=abs(math.atan2(math.sin(th4-math.pi),math.cos(th4-math.pi)))
    assert reverse_error<math.radians(.1)
    return {'straight_1m_spin_rad':spin,'expected_rad':-1/RADIUS,
        'steering_same_distance_speed_invariant':True,'stationary_no_drift':True,
        'reverse_alignment_error_deg':math.degrees(reverse_error)}
if __name__=='__main__':print(validate())
