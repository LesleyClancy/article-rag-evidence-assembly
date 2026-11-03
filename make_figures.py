"""Deterministic manuscript figures from retained numerical data and method definitions."""
from pathlib import Path
import json, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("RAG_FIGURE_DIR", str(HERE / "generated_figures")))
OUT.mkdir(parents=True, exist_ok=True)
DATA = json.loads((HERE / "data" / "figure_data.json").read_text(encoding="utf-8"))
plt.rcParams.update({
    "font.family":"sans-serif", "font.sans-serif":["Arial","DejaVu Sans"],
    "font.size":8, "axes.titlesize":9, "axes.labelsize":8,
    "xtick.labelsize":7.5, "ytick.labelsize":7.5,
    "pdf.fonttype":42, "svg.fonttype":"none",
    "axes.spines.top":False, "axes.spines.right":False,
    "axes.linewidth":0.7, "legend.frameon":False,
    "savefig.facecolor":"white",
})
BLUE="#356E9C"; TEAL="#267F75"; ORANGE="#BC7534"; GRAY="#737C85"
INK="#263442"; PALE="#E9F0F6"; LIGHT="#F2F4F6"
W=170/25.4

def save(fig, name):
    fig.canvas.draw()
    # Fixed physical canvas, no tight-crop change after geometry inspection.
    fig.savefig(OUT/f"{name}.svg")
    fig.savefig(OUT/f"{name}.pdf")
    fig.savefig(OUT/f"{name}.png",dpi=600)
    fig.savefig(OUT/f"{name}_preview.png",dpi=300)
    plt.close(fig)

def plain(ax):
    ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off")

def label(ax, s, title):
    ax.text(0,1.03,s,transform=ax.transAxes,weight="bold",fontsize=10,va="bottom")
    ax.annotate(title,xy=(0,1.03),xycoords="axes fraction",xytext=(12,0),
                textcoords="offset points",fontsize=9,va="bottom")

def box(ax,x,y,w,h,text,face=LIGHT,edge="#B8C4CE",size=8):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=face,edgecolor=edge,lw=.7))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=size,color=INK,linespacing=1.35)

def arrow(ax,a,b,color=GRAY,style="-"):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=9,lw=.9,color=color,linestyle=style))

# Figure 1: processing dependencies, then study scope. No references flow into generation.
fig,axs=plt.subplots(2,1,figsize=(W,128/25.4),gridspec_kw={"height_ratios":[1,1]})
fig.subplots_adjust(left=.035,right=.985,bottom=.065,top=.91,hspace=.48)
for ax in axs:plain(ax)
a,b=axs
label(a,"a","From source material to an evaluated answer")
nodes=[(.00,"Versioned\nmanual"),(.205,"Source units\nand retrieval"),(.410,"Budgeted\nevidence"),(.615,"Fixed\nanswer model"),(.820,"Answer and\ncitations")]
for x,t in nodes:box(a,x,.57,.18,.31,t,PALE)
for i in range(4):arrow(a,(nodes[i][0]+.18,.725),(nodes[i+1][0],.725))
box(a,.00,.05,.35,.28,"Locked reference facts\nEvaluation only",LIGHT)
box(a,.46,.05,.54,.28,"Delivery checks + human answer evaluation",face="#E7F0ED",size=7.8)
arrow(a,(.35,.19),(.46,.19),TEAL)
arrow(a,(.50,.57),(.55,.33),TEAL)
arrow(a,(.91,.57),(.91,.33),TEAL)
label(b,"b","Sequential studies with different inferential roles")
phase=[("ACS580","Initial pipeline\nand retrieval baselines"),
       ("ATV320","Parser adaptation\nand development"),
       ("V20","Assembly controls\nand budget diagnostics"),
       ("V90","Limited adaptation\nthen new-source follow-up")]
for i,(name,desc) in enumerate(phase):
    x=i*.255
    box(b,x,.39,.235,.44,name+"\n"+desc,PALE if i<3 else "#E7F0ED",size=7.6)
    if i<3:arrow(b,(x+.235,.61),(x+.255,.61))
b.text(.5,.15,"Separate versions and exposure histories; not four independent tests of one frozen system.",
       ha="center",va="center",fontsize=7.3,color=INK)
save(fig,"Fig1_workflow")

# Figure 2: abstract method diagram, not a fabricated experimental example.
fig,ax=plt.subplots(figsize=(W,116/25.4))
fig.subplots_adjust(left=.035,right=.98,bottom=.04,top=.94)
plain(ax)
ax.text(0,.98,"Shared ranked hit → original parent → expansion → budget admission",weight="bold",fontsize=9,va="top")
for x,txt in [(0,"Previous page"),(.335,"Anchor page"),(.67,"Following page")]:
    box(ax,x,.72,.315,.17,txt+"\nOriginal source units",PALE)
ax.text(.5,.675,"Expansion scope and admission granularity vary; source text and ranking are fixed.",
        ha="center",va="center",fontsize=7.6)
rows=[
("B0","Hit parent only","Individual parent"),
("B1","Hit parent, previous page, following page","One unit at a time"),
("B1A","Same neighboring-page window as B1","New window members together"),
("BT","Anchor table + matching neighboring tables","New group members together"),
("B2","Parameter boundaries across eligible pages","New group members together"),
]
for i,(name,scope,admit) in enumerate(rows):
    y=.555-i*.087
    ax.text(.02,y,name,color=TEAL if name=="B2" else INK,weight="bold",va="center",fontsize=9)
    ax.text(.13,y,scope,va="center",fontsize=7.4)
    ax.text(.72,y,admit,va="center",fontsize=7.3)
ax.text(.13,.612,"EXPANSION",fontsize=7,color=GRAY)
ax.text(.72,.612,"ADMISSION",fontsize=7,color=GRAY)
box(ax,.00,.025,1,.105,"Deduplicate → test complete-message ceiling → stop at first overflow\n"
    "Keep previously admitted units. B2 preserves whole parents, not parameter-only excerpts.",
    "#E7F0ED",size=7.3)
save(fig,"Fig2_assembly")

# Figure 3: all methods at every budget + paired direction, not marginal-only comparison.
fig,axs=plt.subplots(1,2,figsize=(W,90/25.4),gridspec_kw={"width_ratios":[1.15,1]})
fig.subplots_adjust(left=.09,right=.98,bottom=.22,top=.82,wspace=.37)
a,b=axs
label(a,"a","Complete evidence delivery")
label(b,"b","Paired B2 versus B1 outcomes")
caps=[4000,8000,12000,16000,20000]
colors={"B0":"#8A9096","B1":BLUE,"B1A":"#81709B","BT":ORANGE,"B2":TEAL}
markers={"B0":"v","B1":"s","B1A":"D","BT":"^","B2":"o"}
styles={"B0":":","B1":"--","B1A":"-.","BT":":","B2":"-"}
for arm in colors:
    vals=[next(r["complete"] for r in DATA["grid"] if r["cap"]==cap and r["arm"]==arm) for cap in caps]
    a.plot(np.array(caps)/1000,vals,label=arm,color=colors[arm],marker=markers[arm],
           ls=styles[arm],lw=1.4 if arm=="B2" else 1.0,ms=4,markerfacecolor="white" if arm!="B2" else TEAL)
a.set_xticks([4,8,12,16,20]);a.set_yticks([0,6,12,18,24]);a.set_ylim(0,25)
a.set_xlabel("Whole-message ceiling (thousand tokens)")
a.set_ylabel("Questions with all listed facts (of 24)")
a.grid(axis="y",color="#DCE1E5",lw=.5)
a.legend(ncol=5,fontsize=7,loc="upper left",bbox_to_anchor=(-.08,1.28),columnspacing=.8,handlelength=1.6)
y=np.arange(5)
wins=[r["win"] for r in DATA["paired"]]; losses=[r["loss"] for r in DATA["paired"]]
b.barh(y,wins,height=.48,color=TEAL,label="B2 only")
b.barh(y,[-v for v in losses],height=.48,color=ORANGE,label="B1 only")
b.axvline(0,color=GRAY,lw=.6)
for j,(win,loss) in enumerate(zip(wins,losses)):
    if win:b.text(win+.18,j,str(win),va="center",fontsize=8)
    if loss:b.text(-loss-.18,j,str(loss),ha="right",va="center",fontsize=8)
b.set_yticks(y,["4k","8k","12k","16k","20k*"]);b.invert_yaxis();b.set_xlim(-3.5,7.5)
b.set_xticks([-2,0,2,4,6]);b.set_xlabel("Paired question counts")
b.legend(loc="upper left",bbox_to_anchor=(-.06,1.28),ncol=2,fontsize=7)
fig.text(.5,.055,"*20k: the single B2-only case is Q04, with limited alternative-source annotation.\n"
         "Mechanical delivery only; the same 24 questions recur across budgets.",ha="center",fontsize=7,linespacing=1.4)
save(fig,"Fig3_budget")

# Figure 4: every V90 response position plus the distinction hidden in aggregate rates.
fig,axs=plt.subplots(1,2,figsize=(W,99/25.4),gridspec_kw={"width_ratios":[1,1.1]})
fig.subplots_adjust(left=.045,right=.985,bottom=.18,top=.84,wspace=.22)
a,b=axs
plain(a);plain(b)
label(a,"a","All 24 rated answer positions")
label(b,"b","What failed in the four non-passing answers")
cols=[(4000,"B1"),(4000,"B2"),(12000,"B1"),(12000,"B2")]
for j,(cap,arm) in enumerate(cols):
    a.text(.25+j*.205,.92,f"{cap//1000}k\n{arm}",ha="center",va="center",fontsize=8)
for i in range(6):
    yy=.78-i*.112
    q=f"V90-N{i+1:02}"
    a.text(.045,yy+.035,f"N{i+1:02}",ha="left",va="center",fontsize=8)
    for j,(cap,arm) in enumerate(cols):
        r=next(r for r in DATA["v90"] if r["id"]==q and r["cap"]==cap and r["arm"]==arm)
        state="P" if r["pass"] else ("S" if r["input_support"]<2 else "R")
        color={"P":"#DDECE7","S":"#F3DEC9","R":"#E2E7EC"}[state]
        box(a,.17+j*.205,yy,.16,.07,state,color,size=8)
a.text(.02,.055,"P  Strict pass    S  Support failure\nR  Incomplete answer with honest refusal",fontsize=7.2,va="center",linespacing=1.4)
details=[
("N01 · B2 · 4k","Correct target content, but cited\nanother filter's parameter entry."),
("N03 · B1 · 4k","Correct facts inferred beyond\nthe actual input evidence."),
("N04 · B1 · 4k","Supported refusal, but the\nrequired answer was incomplete."),
("N01 · B2 · 12k","All necessary facts delivered;\nadditional manual-wide claim unsupported."),
]
for i,(title,desc) in enumerate(details):
    yy=.87-i*.215
    b.text(0,yy,title,fontsize=8,weight="bold",color=INK,va="top")
    b.text(0,yy-.063,desc,fontsize=7.6,color=INK,va="top",linespacing=1.35)
fig.text(.5,.05,"Six questions with sufficient evidence on one page; one answer per condition; one human reviewer.\n"
         "At 12k, both methods delivered every listed necessary fact, but B2 failed support on N01.",
         ha="center",fontsize=7.2,linespacing=1.4)
save(fig,"Fig4_v90")
print("Created four editable figures with numerical source data.")
