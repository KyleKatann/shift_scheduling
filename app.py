import streamlit as st
import pandas as pd
import glob
import plotly.figure_factory as ff
import plotly.express as px
import datetime
import networkx as nx
import random
from mypulp import*

#スケジューリングするまえのjob
def drawrawwork(jobs):
    dt1 = datetime.datetime.now()
    df = []
    c=0
    for s,e in jobs:
        df.append( dict(Task="仕事"+str(c), Start=dt1 + datetime.timedelta(minutes=s), Finish=dt1 + datetime.timedelta(minutes=e), Resource='job') )
        c+=1

    colors = dict(job = 'rgb(198, 47, 105)')

    fig = ff.create_gantt(df, colors=colors, index_col='Resource', title='job Schedule',show_colorbar=True, bar_width=0.1, 
                          showgrid_x=True, showgrid_y=True)

    st.plotly_chart(fig, filename='gantt-hours-minutes')

#スケジューリングした後のjob
def draw(jobs,dworkerwork):
    dt1 = datetime.datetime.now()
    df = []
    for wk,w in sorted(dworkerwork.items(),key=lambda x: int(x[0].replace("作業員",""))):
        for wnumber in w:
            num=int(wnumber.replace("作業",""))
            df.append(
                dict(Task=wk, 
                     Start=dt1 + datetime.timedelta(minutes=jobs[num][0]), 
                     Finish=dt1 + datetime.timedelta(minutes=jobs[num][1]),
                     Resource=wk
                    )
            )
    colors = {worker :"rgb("+str(random.randint(100,255))+","+str(random.randint(100,255))+","+str(random.randint(100,255))+")" for worker in dworkerwork.keys()}
    


    fig = ff.create_gantt(df, 
                          colors=colors, 
                          index_col='Resource',
                          title='job Schedule',
                          show_colorbar=True, 
                          bar_width=0.1, 
                          showgrid_x=True, 
                          showgrid_y=True, 
                          group_tasks=True)

    st.plotly_chart(fig, filename='gantt-hours-minutes')


def drawqualifications(qualifications):
    workers=[]
    canwork=[]
    for k,v in qualifications.items():
        for i in v:
            workers.append(int(k.replace("作業員","")))
            canwork.append(i)
    st.write( px.scatter(x= canwork , y= workers , labels={'x':'仕事番号', 'y':'作業員番号'}) )


@st.cache
def opt(jobs,qualifications):
    G=nx.Graph()
    for i in range(len(jobs)):
        for j in range(i+1,len(jobs)):
            s1,e1=jobs[i]
            s2,e2=jobs[j]
            if not(e1<=s2 or e2<=s1):
                G.add_edge(i,j)
    cliques=tuple(map(set,nx.find_cliques(G)))
    
    m=Model("shift")
    try:
        m.params.MIPFocus = 3
    except:
        pass
    x,y={},{}
    
    for worker in qualifications:
        y[worker]=m.addVar(vtype="B",name=worker)
        for work in qualifications[worker]:
            x[(worker,work)]=m.addVar(vtype="B",name=worker+"_"+str(work))
    m.update()
    
    for work in range(len(jobs)):
        m.addConstr( quicksum( x[(worker,work)] for worker in qualifications if (worker,work) in x)==1 )
    
    for worker in qualifications:
        for clique in cliques:
            m.addConstr( quicksum( x[(worker,job)]for job in clique&qualifications[worker]  )<=y[worker] )

    m.setObjective(quicksum( y.values() ), GRB.MINIMIZE)
    m.optimize()
    
    dworkerwork={}
    dworker=[]
    if m.Status == GRB.Status.OPTIMAL:
        for v in m.getVars():
            if v.X:
                ans=v.VarName.split("_")
                if len(ans)==2:

                    if ans[0] in dworkerwork:
#                        print(ans[1],end=" ")
                        dworkerwork[ans[0]].append(ans[1])
                    else:
#                        print("\n",ans[0],ans[1],end=" ")
                        dworkerwork[ans[0]]=[ans[1]]
                else:
                    dworker.append(ans[0])
        minimum=m.ObjVal
#    else:
#        print("infeasible")
    #print(x)
    return dworkerwork,dworker,minimum



@st.cache
def load_data(filename):
    _,filenumber,number_of_workers,number_of_jobs,multi_skilling_level=filename.replace(".txt","").split("_")
    filenumber,number_of_workers,number_of_jobs,multi_skilling_level=map(int,[filenumber,number_of_workers,number_of_jobs,multi_skilling_level])
    file=open(filename).readlines()[5:]
    jobs=[tuple(map(int,line.split())) for line in file[:number_of_jobs]]
    qualifications=[tuple(map(int,line.replace(":","").split()))[1:] for line in file[number_of_jobs+1:]]
    qualifications={"作業員"+str(k):set(v) for k,v in enumerate(qualifications)}
    return jobs,qualifications

#data_load_state = st.text('Loading data...')
#data = load_data(10000)
#data_load_state.text("Done! (using st.cache)")

'''
# shift minimization personnel task scheduling

## 問題設定\n
n個の時間が決まった仕事があり、m人の作業員がいます。\n
作業員は時間が被らないように一日に複数の一仕事ができます。\n
しかし、作業員はn個の仕事が全てできるわけではなく、資格という形で遂行可能な仕事がn個未満に決められています。\n
このとき、全ての仕事をこなすための最少人数は何人ですか？\n

## データ

'''

filename = st.selectbox('ベンチマーク問題を選んでください', sorted(glob.glob('./texts/*.txt'),key=lambda x: int(x.split("_")[1])) )
st.write('あなたが選択したのは', filename)

data_load_state = st.text('ファイル読み込み中...')
jobs,qualifications = load_data(filename)
data_load_state.text("ファイル読み込み終了!")


if st.checkbox('時間が決まった仕事のガントチャートを見る'):
    drawrawwork(jobs)
if st.checkbox('作業員の資格表を見る'):
    drawqualifications(qualifications)

'''
## 演算結果
'''
dworkerwork,dworker,minimum=opt(jobs,qualifications)
draw(jobs,dworkerwork)
st.text('最少人数'+str(int(minimum))+'人')
for worker in sorted(dworkerwork.keys(),key=lambda  x: int(x.replace("作業員","") )):
    st.text(str(worker)+":   "+" ".join(["仕事"+w for w in sorted(dworkerwork[worker])]))