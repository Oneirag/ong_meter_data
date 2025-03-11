import requests

headers = {
    'Accept': '*/*',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8,it;q=0.7',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'text/plain;charset=UTF-8',
    'DNT': '1',
    'Origin': 'https://www.i-de.es',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

data = '{"sensor_data":"3;0;1;0;3425602;6m60QzXfl+Umv/nBs9pq8xz8I3AEe0/u+Q8OXlkcOQ4=;10,18,0,0,4,194;]]H~8vREkvM\\"_Jh,\\"Pn:\\"LKY\\"*5,;xX9L\\"Jg\\"9zlXV<9yE|6\\"%b4%\\">99TU\\"cM@y\\"ir7ZX=}}n\\"E.y\\"O=@{=\\")@<\\"&s/\\"*,O\\"nb.cO\\"#|2\\"Q\\" U.9\\"p\\"#~K\\"A\\"^j/~\\"X\\"-2u\\"a\\"w7R7G/&#ir*R9qu<?w1`ufg:.n :!J{$;aoxtXwR}.q(nvb EslZwViyY8avF5SRxe%rubb=(ZGF5MT5LE,q*PC-q_$>-t$n4. 9eSxTa%GJ*CY\\".t(\\"n6b\\"2v@ia*B>\\"p#8\\" +jgy\\"03@\\"T!^|M%H\\"sg]\\"}p`JwT\\"\\"/aN\\"KK}\\"g\\",vz<A<k<*QAUhTX2Z<uC/Ab=_lujedeN%p0uv[HkCarp\\"B\\"Za!\\"):}6koA*\\"[B_\\"A[1cP\\"c49\\"DH`4mp_9E\\".g\\"5oT\\"X6{.\\"6WIpxRM.z:s,0jZSd#\\"o$q\\"J\\"\\"=\\"vMe\\"!\\"AHJ5;\\"sN%\\"Eu\\"IHd5q\\"uYN\\"NNl1--WT}wCK>Px(=~]RGRF_=aWxg?4[$I|V;W>_<0~El$v|H$Ew)J|.q<uVZJ~Y8Hg\\"i\\"?}e\\",!-0*3jS!G86UzA(l\\"-mw\\"Q\\"TjU(|cD( )a\\"\\"c\\"{@w\\"<\\"!kHC%*mi=(Nq#$Mzzcgj#&=<L6)R-%,d*p^[LK84rY8]^iEpln|n9K`iui^/tv)R~n`g`[Z_J-g6OL+ah`ws7N )5)9kVXiDscaaUn_i]^:jy2qJYTop8O}%RMT9|\\"=\\"6:-\\"Wq``jrW\\"@V<#5-Vp\\"G$#\\"G?$\\"_h]:=v:8\\">PA\\"i\\"\\"cb@\\"8qw\\"Bt0_aiV<\\"ePC\\"i\\"rs8STL9\\"m\\"iCq\\"o\\"Y\\"GDH\\"Wh\\",=)m$0_\\"*2Oj=4+y49+&<nw54vAjOA@@WT?4=_Xo8:B=VL8gHwj5<M<!bJk~%\\"<\\"Q1r\\"Xb\\"6I7\\"D[_\\"Y14.Uq[%]?|\\"{2ri\\"c\\"7\\"Gb#\\"v*R\\"Z\\"]\\"[v]\\"A `\\"R\\"yb4_hpE!*-Qf=b9b>d{}\\"Y\\")El\\"F\\"o\\";}Z\\"QOh\\"c\\"o-[)L4l;a/8>2f}9i4%daKH*{H0=H4{9?k;%L5aRa<JRG6DcBu`PL4F*|R/BkPCa`Dgb,zSAc9NfWCgwhF7z5u!uhK-QlkSv$`/,[S1(P$SpUTz>xSYQZUhQb/*Ohdbv6zNA1!g`2k1aYLxC,p(t($8.)zd+]]^!G$ifAI/&aOf7?5i=3v*,BEW[gS?rMCGu7+nj_ZCI-p:ux&Y-{z|$M_tk-|$K%5/i5,blhkUgEAhCQa9hpfy.AYtx80D\\"F\\"Oqc\\"a\\"S\\"QsL\\"hJG\\"q\\"G>bs<P%}EIN3h+0yaJ;IDfftWh5,;@,z~.?V}B{&ND[@)IQC~}x41MFfhcA7Mh@.EQz+W(MyGGKD/XoY7FPdc &OMY:&KgPHbjF_0]2V!6H84SthVYm./[]0&<x|9jYYs|WzMzZ$[o6w(W~fat~>Mx2J[}mV)_UTh.j)rB!H%Dlgq:f]SupKa@Q}}65*h=8@]#p/pQBuUo189pFSIbuJc=`7Ome[>sv$NqR4uXM|c1bey={!)GgB]AeEbxs&dIXW7I@rwXM2h6p{*nT]h$P!H.U>[$+Dylw!^+!VbA8}jHs+?%i%)f)[;yQ.T{-N3&/P!bA28)+cg0t/A8$:>zK8Y](|Fz~>3z@k?vg`kRYNM~w%F03Ka?h^2$YTu[n:6yFYK$,--!1|~dHn476RhGskUN$$M4Psul5c^4D-F<TOZG~Nsyu=fJ)$m`F:#^/YMS/V?6A<YKni{]T!U`]-`?x}izjb> Mz#1g;({98K_zs0|!L$/3o<.amam[mIHqDOR5jlY|)DV#%21-lHOg;ehWSXjSmPIs`i{i5C-P]+Ekx+9CsZr,mK;0/<BJRLF|` 3k`eh78qvL]2(@~dzByM]Prp%$>;6sg <%p{+IcDY3H{i/pZz:*guv+5Xe{ )pRl9-w&<c%i*T%Les[Wm?!n(#AN#,KD[QHc-,r*5z>w@~E#&HI9i6|~x%Fe4Kun&&s8qbf19q9*P8^EWrz}Mhkg)-Sm7Zw8H@ErKQEd/d71UAiQe<69 DM>fpQa?b7BZf^;m|z@hJ&t[D i,WP^;|)#GL5V;V5Er}{W1AAxK1saG: _2X`(a<CDh7n?vC(:rs,iIioIna8:,x`K{^w{gLfl?g;mV.r+a`}nQ^}X?+f{La<6pQkxrX{rU)kG0U>p=ZzdQk2sHA&>(:{oD7CrhXr a/{MV*nJ&7VG5f}vTN:QG@KC~o5OKKhzh=%jaD2aMi82/TjgDIIRW^^[M8d4-5YzK6 uxXM~x2ZXf9aQ>I5ZTim$iU)Z^[:_E1#gk_V<2Z,(3_/+u-)UN|i)lqK  ,[.%WsYkXX@%^1CL&]XQip/Hoq4w{T97G2]S8GGXBIC0iDO^=v&}=Kl$K_kpwXDRe;qgd{|)!.-!REZlW<E1aq:a+<[]rO.[oQ/5$7@J_sluC*UhQ<NO|7k#Si:LW7{HjT)>=][)!>9E3w=bB1HZvH$Bp5g|4 d/UQ09FXk1E[nrbYu=+#4N1T4F2_15f[Mh2428AUl9Rx-@~}Hzil,Mo91ZHc6WuysK hh).JhJY0<I>DhFJOk)h> H>jRv44:s?CBYi7Y9Q%1Y][7g_m/YBtf=2]Ld8HE5lnf*?!B(Jo7YWQ;&37l0fK6#tNCi?KY3p!#XlOv^{^wMRN;~:AzE9}wUX2|U5?YB{8@m2gC(W?[32H/}?S$QP2={$lh9t.=:t>GwJ aE m)g ?,h$C%eXVP8G//oAg%(q2=~F>wlE.[5WiUS J!a^SN]_NN(t?e]Lq7}C3mvFJs^|=;5_%]NaWWRjYmHDm0(2Rm`?9ke]H1u6SaR-MC8>:SOys}QYzNU^(J/{!lbYR-&JshtQ!xuw}9Iagle`6j~|HniKHNN8A*~Sy)1lFO7LRn*@SgaU:l$(o17%)q!{ tlC}(4)f_Ov|Ka$2EIJ0j*BsFP6@A[PeZ`&c&9#Urb/;o#Tg-,@|j|*mG[Mjay|3*3_Rq+&_rb0D)<~2SZteCe{qW_Ztk7<RN]?8@saRVdAc8Y0C~x:3 HtILLN`zHJzx}dUzIE0QY#X-d/[<HfTOk9-|C5dk;Sxy.!zAuyn(DjD$T7e=Qxni:rkfl}E^9Br2E1/V6<;YxR!t@-S2Vpw!V*4|DV!>y4l0=29hGQ[}C,[H$pQ/T)*=lGP<cwT RxR^.6<qRZl7`E,x]](y3o)5kRUV/>yK0U Gs/+gPcn@maD>#|cX#Rcq`=Od@[9e@v[!W_oS=WjD$nOTAQz!VBLfP6WSB^:!gC}Ax6P++Og9rmljKUBA{e{22|AP(Q?+cQDgDWype ;*idVbXnXU6vFmUK|?p>0m~NCuYp054Z kUM>VWhT[Q9W,++FgX&%]iMK%b/FELzH0 /-3;^a`P@m;?Fs>~Y`Q@3:zb$R`d0gZOadxx=6SIKtLZ[!PE6,{-y ]I!ZbkIoyn((TZ~-<21eGOS8jfILL^PgF<sDYhV%%{=Il+IT rzJ/O`AsoNpiuz/o%O)9ZE &-Gg{6i/QUQ/z2J:tnixu,0JF:.e21#n+yBm/R&A`v,v_y9tToljzJLTYiX/[|fQnq;]=e=U .=9(Hk]ECNtz:PkpumOuGF/Fa0M2a5K&?_F;k>){0=Kc6Mpw)yr8`[b# c7s9yI;Dh[[{XMJc`9I%8Ri,)rC%!u9X<hP*n5t4WiaDofg~5d2LmQOxotM 22^mY3#`M)e-QPh;ox}DN{K*Z)C]hd?s$2o,}L?!|VCc1?S-e~/Ha<lB{Eg9KK5h#.a5yU_:<pj4#|:rbr#@hQ#`1{=^s0zLu%b*%`rRS51aJOqeAZiBqP&pN!M1BM?2ZbLu{WjN^OJ$b-M/(EW RLtiD1tH`tlR&9*liPcKcRN3u;fMBi#sB4p`;5jMr1&w>wJA=(CDOGP;+Guok0N0xsUN4*cEh2(-g,xhvy*,:9@.vK#{~Qq^35%/rjPEa6:ChC;%5>RRv~2ssOu,/Z%q^iMYGZ,1T.*?dEJ4WM!2<GaUW/sx*a,-j~rxh!X]7vy0dMAFZe(Nl!/&1qRi ]}/j&&@-M-0_AdlM5DJXcBW|;W]UL%JeKs#o4!DHRFP5~$E+*)%Mv:]!Ffv%iX{4wZc[y-G:TTnJ5J$dX]r6X;U+Nnz7)yC_V6?=ep,CnavQLt>8y8Eo8}<zB|$C..h(y`#zIJ|1YdpZXpGEBZpO|Lz`B\\"w\\"uq9\\":&=Om.Vx7-YE\\"S&0>\\"<k?._JuJ`-u\\"U%(\\"V\\"4P}>s%A<EpQNd(M ZVvtX\\"H\\"aWL\\"D\\"\\"p\\"I.U\\"^\\"*\\"V5A\\"o2r\\"rK,fD\\"ABV\\"4<<b{M$S\\"N`0\\"rGw,+\\"#f\\"sWEf`T\\"2C}l}$W Z6\\",z7\\"^jS\\"|+R1z\\"Q(G{\\"viD\\"6/;\\"J\\"G)oJ2O#7T=8R^@\\"aZP\\"Fus\\"]z8&]$/\\"(xK\\"?,K*.\\"(xr\\"%\\"UCK>\\"19c\\"nyy\\"ayN0raQ/y@/?\\"E9r(\\".\\"|2+s*6w80[!xoaM#@d2m4B#Ku9nDlSDPC%atsIcWR*[.OH[j<`^zDTb/.ejh88X1\\"ny(\\"(}y\\"L\\"VzJE*(#%ucKDuK^d8ha]ot>P[i zwQ47D|FL8+(=0B|kG+9H!f`Xc|DWu%HHF#aq%d74/7~M<P8;iYdse:EFe|SX$Bf[aP3OY7,%p/1AG[ET-x4H6~%$We9Y&AopzdRv!s_Z^wh/<RR[B#KfN<Sh)@|9.7]m-|k+I?#7+IX}2NKVC,U~lbz-Zu^(e%Za1(u7i^:JU-<Zo0FQ9&`)}u4G)F!W?lFQxsq>keQh!Kb2Flu01zSx$%Id7jW$p;{7lU^:ohf#0g%Ka>Xhcf:l#rBlIzgD1gKn57O~bbf#Ac+a2]p;:?(RVm@aS&#PN!n2hm)_E@Mp!k-n8!=_dbF3HQ%[Hyw`L7{R5AH+y)+]~c7vG&Ojn(qV{3f:9paYW34[EYy\\"B\\";}6\\"(\\"<&E$ @+t1V\\"Y[6\\"2w}\\"mBhorQ\\"p>\\"-\\"\\"yf4\\"k&*\\"a Y=Cz2%@qqA\\"GqRW\\"W\\"mZx1id3v\\"E\\"l:j\\"Y\\"{@Z),\\"<.M\\"jQv\\"O\\"\\"Y\\"$d9\\"!:2&Dg3\\"\\"d\\"Yty\\"7j\\"YP`\\"rV4sRNr\\"\\"|Rn\\"m0i\\"|{%0?K\\"J:9]\\"s\\"=bK96+*)\\"^\\"n7<\\"S\\"LMV`{.JQjSj@w|+d/QLAxCA2Vu$!fCYV0MMvxPV+|C,w=jaX\\")xw\\"-| \\"@q5^h\\"el \\"v7VQl`TS~_ud\\"wsizz,.DA3~V{\\"#\\"LPy\\".\\"t,NbiMC^w`;HCb_ |C9<-j8H629El$e,_sGRbUCf(q]hh+/RX$$1li#PE8\\"Z\\"4m:\\"k,+M0\\"MooP\\"4Lc/>[hfaG\\"8y~\\"$Es8[r0le6~\\"AjX`b N\\"V\\"Z~(v|kmxg8YNc=wn\\"6\\"PQc\\"#\\"q7\\"b1W\\")=OW\\"Y\\"\\")\\"G7a\\"^\\"\\"O\\"q%8\\"q7N\\"tJ~\\"Bd&=DN(aYs(\\"/e\\"g\\"BUvGMRWX)xs}dH+El5;7MOGu-Y)mm!.$.o77LS!\\"nz?\\"6^7\\"v\\"vJWC!?gjXG]Q>UJ5I-.=x0U4e{q=>3L_b[w+ 82\\"@Bv\\"neS\\"S\\"\\"I#>\\"U#H\\"D\\"W\\"eLP\\"WDw\\"@ol18Bm\\"T+\\"$_;\\"ER8y\\"n\\"1![9\\"ieQ\\"8~^\\"!\\"drtpUp%RVHkve,\\"bbB38\\"F\\"\\"T\\"&}\\"72;G?TK\\"pF~\\"C\\"JEv3E\\"stE\\"Eu|{u\\"F\\"\\"/\\"&R@\\"pe<DYGQ\\"cs|ek5eulchlN+&Zt)= Sz.9*67vTZ(bTD?@Gk=+RPY8tNd[.uNI)s-OkwOh>*+n\\"oWh"}'

def run_eks(client):
    response = client.post(
        'https://www.i-de.es/kQcwL4CjJ/D7F/6ZZ/hMKA5WdlXFMc/zOX5DSJXkVLDYL3m/IB4VP0sEBw/MRwBRTdh/eks',
        #cookies=cookies,
        headers=headers,
        data=data,
    )
    # print(response)
    # print(response.content)
    return response.json()


if __name__ == "__main__":
    client = requests.Session()
    print(run_eks(client))

