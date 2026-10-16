"""Direct vector drawings for the launch-indexed timing examples."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,FancyArrowPatch
plt.rcParams.update({"font.family":"STIXGeneral","font.size":9,
                     "mathtext.fontset":"stix","pdf.fonttype":42,"ps.fonttype":42})
def canvas(size,xlim,ylim):
    fig,ax=plt.subplots(figsize=size)
    fig.subplots_adjust(left=.015,right=.985,bottom=.025,top=.975)
    ax.set(xlim=xlim,ylim=ylim);ax.set_axis_off()
    return fig,ax
def arrow(ax,start,end,label=None,at=None,rad=0,style="-",width=.7):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle="-|>",mutation_scale=9,
                 connectionstyle=f"arc3,rad={rad}",linewidth=width,
                 linestyle=style,color="black"))
    if label:ax.text(*at,label,ha="center",va="center")
def save(fig,ax,out,name):
    fig.canvas.draw()
    for label in ax.texts:
        b=label.get_window_extent()
        if b.x0<fig.bbox.x0-1 or b.y0<fig.bbox.y0-1 or b.x1>fig.bbox.x1+1 or b.y1>fig.bbox.y1+1:
            raise ValueError("label outside canvas: "+label.get_text())
    fig.savefig(out/(name+".pdf"),metadata={"CreationDate":None,"ModDate":None})
    plt.close(fig)
def timeline(out):
    fig,ax=canvas((3.45,2.15),(-1.55,7.25),(-.55,4.65))
    arrow(ax,(-.1,0),(6.9,0))
    ax.text(6.5,-.38,"cycle",ha="center",va="center")
    for x in range(7):
        ax.plot([x,x],[-.09,.09],color="black",lw=.6)
        ax.text(x,-.31,str(x),ha="center",va="center",fontsize=8)
    for y,text in [(2.72,"launch"),(1.72,"$x$ read"),(.82,"$y$ valid")]:
        ax.text(-.38,y,text,ha="right",va="center")
    for x,dash in [(0,"-"),(1,"--")]:
        arrow(ax,(x,2.34),(x,2.92),style=dash)
        ax.text(x,3.12,"$t_0$" if x==0 else "$t_1$",ha="center",va="center")
    ax.annotate("",xy=(1,3.8),xytext=(0,3.8),
                arrowprops=dict(arrowstyle="<->",lw=.7,color="black"))
    ax.text(.5,4.12,"$g=1$",ha="center",va="center")
    for x,y,filled,age in [(0,1.72,True,0),(1,1.72,False,0),
                            (4,.82,True,4),(5,.82,False,4)]:
        ax.plot(x,y,"o",markersize=3.6,markerfacecolor="black" if filled else "white",
                markeredgecolor="black",markeredgewidth=.7)
        ax.text(x,y+(.3 if y<1 else -.3),str(age),ha="center",va="center",fontsize=8)
    ax.plot([0,4],[.18,.68],":",lw=.6,color="black")
    ax.plot([1,5],[.18,.68],":",lw=.6,color="black")
    ax.text(2.5,3.2,"Overlap allowed;\nfilled/hollow events\nmark launch identity",
            ha="left",va="center",fontsize=8)
    save(fig,ax,out,"timeline")
def translation(out):
    fig,ax=canvas((3.45,2.20),(-.55,5.2),(-1.15,2.65))
    nodes={"e":(0,1.4),"a0":(1.65,1.4),"a1":(3.3,1.4),
           "a01":(3.3,-.05),"a12":(1.65,-.05)}
    labels={"e":r"$\varnothing$","a0":r"$\{0\}$","a1":r"$\{1\}$",
            "a01":r"$\{0,1\}$","a12":r"$\{1,2\}$"}
    for n,(x,y) in nodes.items():
        ax.add_patch(Circle((x,y),.31,facecolor="white",edgecolor="black",lw=.7,zorder=3))
        ax.text(x,y,labels[n],ha="center",va="center",zorder=4)
    arrow(ax,(.33,1.4),(1.32,1.4),"launch",(.82,1.67))
    arrow(ax,(1.98,1.4),(2.97,1.4),"tick",(2.48,1.67))
    arrow(ax,(3.3,1.07),(3.3,.28),"launch",(3.8,.68))
    arrow(ax,(2.97,-.05),(1.98,-.05),"tick",(2.48,-.34))
    arrow(ax,(1.33,-.12),(-.12,1.07),"ticks/\ndrop",(.25,-.55),rad=-.35)
    arrow(ax,(1.40,1.63),(1.90,1.63),rad=-2.5)
    ax.text(1.65,2.36,"need: $x@0$",ha="center",va="center")
    arrow(ax,(3.52,.16),(3.52,-.25),rad=-2.8)
    ax.text(4.35,-.72,"sample: $y@1$\nneed: $x@0$",ha="center",va="center",fontsize=8)
    save(fig,ax,out,"translation")
def branching(out):
    fig,ax=canvas((3.45,1.95),(-.8,5.75),(-.7,3.1))
    nodes={"i0":(0,2.4),"i1":(2.5,2.4),"if":(5.2,2.4),
           "s0":(0,.45),"sb":(2.5,1.05),"sc":(2.5,-.2),"sf":(5.2,.45)}
    labels={"i0":"$i_0$","i1":"$i_1$","if":"$i_f$","s0":"$s_0$",
            "sb":"$s_b$","sc":"$s_c$","sf":"$s_f$"}
    for n,(x,y) in nodes.items():
        ax.add_patch(Circle((x,y),.26,facecolor="white",edgecolor="black",lw=.7,zorder=3))
        ax.text(x,y,labels[n],ha="center",va="center",zorder=4)
    ax.text(-.6,2.4,"$I$",ha="center",va="center")
    ax.text(-.6,.45,"$S$",ha="center",va="center")
    arrow(ax,(-.6,2.92),(-.12,2.65));arrow(ax,(-.6,.97),(-.12,.70))
    arrow(ax,(.28,2.4),(2.22,2.4),"$a$",(1.25,2.65))
    arrow(ax,(2.78,2.4),(4.92,2.4),"$b$",(3.85,2.96),rad=-.32)
    arrow(ax,(2.78,2.4),(4.92,2.4),"$c$",(3.85,1.83),rad=.32)
    arrow(ax,(.28,.52),(2.22,.98),"$a$",(1.15,1.0))
    arrow(ax,(.28,.38),(2.22,-.13),"$a$",(1.15,-.13))
    arrow(ax,(2.78,.98),(4.92,.52),"$b$",(3.95,1.02))
    arrow(ax,(2.78,-.13),(4.92,.38),"$c$",(3.95,-.17))
    save(fig,ax,out,"branching")
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir",type=Path,default=Path(__file__).resolve().parent)
    args=ap.parse_args();args.outdir.mkdir(parents=True,exist_ok=True)
    timeline(args.outdir);translation(args.outdir);branching(args.outdir)
    print("Three direct embedded-font vector schematics.")
if __name__=="__main__":main()
