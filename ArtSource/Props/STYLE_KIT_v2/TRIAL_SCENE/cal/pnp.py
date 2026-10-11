import numpy as np, sys, json
from scipy.optimize import least_squares
def rot(yaw, pitch, roll=0.0):
    # Unity: Quaternion.Euler(pitch, yaw, roll) applied ZXY; camera forward = +Z
    cy, sy = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    cp, sp = np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
    cr, sr = np.cos(np.radians(roll)), np.sin(np.radians(roll))
    Ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    Rx = np.array([[1,0,0],[0,cp,-sp],[0,sp,cp]])
    Rz = np.array([[cr,-sr,0],[sr,cr,0],[0,0,1]])
    return Ry @ Rx @ Rz
def project(params, P, W, H, fov):
    x,y,z,yaw,pitch,roll = params
    R = rot(yaw,pitch,roll)
    d = (P - np.array([x,y,z])) @ R      # camera-space coords (columns = right, up, forward)
    f = (H/2)/np.tan(np.radians(fov/2))
    u = W/2 + f*d[:,0]/d[:,2]
    v = H/2 - f*d[:,1]/d[:,2]
    return np.stack([u,v],1), d[:,2]
def solve(pts, W, H, fov, x0, fix_roll=True):
    P = np.array([p[0] for p in pts], float); UV = np.array([p[1] for p in pts], float)
    def res(q):
        prm = list(q) + ([0.0] if fix_roll else [])
        uv, _ = project(prm, P, W, H, fov); return (uv-UV).ravel()
    r = least_squares(res, x0[:5] if fix_roll else x0)
    prm = list(r.x) + ([0.0] if fix_roll else [])
    uv,_ = project(prm, P, W, H, fov)
    return prm, uv, UV
if __name__ == '__main__':
    pts = [((626,0.3,541),(500,468)), ((624,0,551.5),(352,447)), ((624.5,0,530),(638,535)), ((632.75,0.4,545.41),(530,422)),
           ((631.97,0.4,540.35),(578,438)), ((634.82,0.4,549.94),(507,405)), ((663,17.4,556),(656.5,193)), ((618,0,555),(250,452)),
           ((667.5,0,527.5),(933,375))]
    best=None
    for yaw0 in range(0,360,30):
        prm, uv, UV = solve(pts, 1280, 720, 60, [600,20,500,yaw0,20,0])
        e = np.sqrt(((uv-UV)**2).sum(1)).mean()
        if best is None or e<best[0]: best=(e,prm,uv,UV)
    e,prm,uv,UV=best
    print('mean err px', round(e,2)); print('pose', [round(v,3) for v in prm])
    for (p,_),a,b in zip(pts,uv,UV): print(p, a.round(1), b)
