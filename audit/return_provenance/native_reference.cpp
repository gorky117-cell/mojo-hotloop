// Expert-maintained C++ references, manually adapted from the original numerical
// bodies. They are benchmark competitors and are never transpiler output.
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <vector>
#include <cmath>
#include <cstdint>
#include <new>

static bool values(PyObject *source, std::vector<double>& out) {
    PyObject *seq = PySequence_Fast(source, "expected numerical sequence");
    if (!seq) return false;
    Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
    try {
        out.resize(n);
    } catch (const std::bad_alloc&) {
        Py_DECREF(seq);
        PyErr_NoMemory();
        return false;
    }
    for (Py_ssize_t i=0; i<n; ++i) {
        out[i] = PyFloat_AsDouble(PySequence_Fast_GET_ITEM(seq,i));
        if (PyErr_Occurred()) { Py_DECREF(seq); return false; }
    }
    Py_DECREF(seq);
    return true;
}

static PyObject *geo(PyObject *, PyObject *args) {
    PyObject *lats, *lons;
    if (!PyArg_ParseTuple(args,"OO",&lats,&lons)) return nullptr;
    std::vector<double> x,y;
    if (!values(lats,x)) return nullptr;
    if (x.size()<=1) return PyFloat_FromDouble(0.);
    if (!values(lons,y)) return nullptr;
    if (y.size()<x.size()) {
        PyErr_SetString(PyExc_IndexError,"coordinate length mismatch"); return nullptr;
    }
    double total=0., r=6371., rad=3.141592653589793/180.;
    for (size_t i=1; i<x.size(); ++i) {
        double lat1=x[i-1]*rad,lon1=y[i-1]*rad,lat2=x[i]*rad,lon2=y[i]*rad;
        double dlat=lat2-lat1,dlon=lon2-lon1;
        double sdlat=std::sin(dlat*.5),sdlon=std::sin(dlon*.5);
        double a=sdlat*sdlat+std::cos(lat1)*std::cos(lat2)*sdlon*sdlon;
        if (a>1.) a=1.; else if (a<0.) a=0.;
        double c=2.*std::atan2(std::sqrt(a),std::sqrt(1.-a));
        total=total+r*c;
    }
    return PyFloat_FromDouble(total);
}

static PyObject *ar(PyObject *, PyObject *args) {
    PyObject *xs,*ys,*zs;
    double ox,oy,oz,dx,dy,dz;
    if (!PyArg_ParseTuple(args,"OOOdddddd",&xs,&ys,&zs,&ox,&oy,&oz,&dx,&dy,&dz)) return nullptr;
    std::vector<double> x,y,z;
    if (!values(xs,x)||!values(ys,y)||!values(zs,z)) return nullptr;
    if (x.empty()||x.size()!=y.size()||x.size()!=z.size()) return PyLong_FromLong(-1);
    double norm=dx*dx+dy*dy+dz*dz;
    if (norm<=0.) return PyLong_FromLong(-1);
    double inv=1./std::sqrt(norm);
    dx=dx*inv;dy=dy*inv;dz=dz*inv;
    Py_ssize_t best=-1;
    double minimum=1e30;
    for (size_t i=0;i<x.size();++i) {
        double vx=x[i]-ox,vy=y[i]-oy,vz=z[i]-oz;
        double t=vx*dx+vy*dy+vz*dz;
        if (t<0.) t=0.;
        double wx=vx-t*dx,wy=vy-t*dy,wz=vz-t*dz;
        double dist=wx*wx+wy*wy+wz*wz;
        if (dist<minimum) { minimum=dist;best=i; }
    }
    return PyLong_FromSsize_t(best);
}

static PyObject *quant(PyObject *, PyObject *args) {
    long long ticks;
    double start,stop,fee;
    if (!PyArg_ParseTuple(args,"Lddd",&ticks,&start,&stop,&fee)) return nullptr;
    if (ticks<=0) return PyFloat_FromDouble(start);
    double price=start,peak=start,cash=0.,units=1.;
    bool in_position=true;
    int cooldown=0;
    std::int64_t state=42;
    for (long long i=0;i<ticks;++i) {
        state=(1664525*state+1013904223)&0xFFFFFFFF;
        double random=state/4294967296.;
        price=price*(1.+(random-.5)*.02);
        if (in_position) {
            if (price>peak) peak=price;
            else if (stop>0. && price<=peak*(1.-stop)) {
                cash=units*price*(1.-fee);units=0.;in_position=false;cooldown=5;
            }
        } else {
            if (cooldown>0) --cooldown;
            if (cooldown==0) {
                if (price==0.) { PyErr_SetString(PyExc_ZeroDivisionError,"float division by zero");return nullptr; }
                units=(cash*(1.-fee))/price;cash=0.;in_position=true;peak=price;
            }
        }
    }
    return PyFloat_FromDouble(in_position ? units*price : cash);
}
static PyMethodDef methods[]={{"geo",geo,METH_VARARGS,nullptr},{"ar",ar,METH_VARARGS,nullptr},
                             {"quant",quant,METH_VARARGS,nullptr},{nullptr,nullptr,0,nullptr}};
static PyModuleDef module={PyModuleDef_HEAD_INIT,"native_reference",nullptr,-1,methods};
PyMODINIT_FUNC PyInit_native_reference(void) { return PyModule_Create(&module); }
