"""Phiếu thẩm định theo cấu phần, giữ bản nháp khi chuyển màn hình."""
import json
import pandas as pd
from scripts.insurance_methodology import RUBRIC, QUAL, GOV_LEVELS, rubric_rows
from scripts.insurance_rating import insurance_rating, anchor_options, INPUT_LABELS

def render_assessment(ticker):
    import streamlit as st
    scope=insurance_rating(ticker)
    if scope.get('RatingBlocker')=='SCOPE':return {}
    saved_key='insurance_assessment_saved_'+ticker
    saved=st.session_state.get(saved_key,{})
    out=dict(saved)
    with st.expander('Phiếu thẩm định theo phương pháp bảo hiểm 2025',expanded=False):
        st.caption('Các điểm tổng hợp phải dựa trên bằng chứng và dự báo. Bảng 10, 11, 13, 15, 18 có nội dung định tính hoặc chồng lấn; phần mềm giữ quyết định thẩm định, không tạo trọng số mới.')
        def select(key,options,help=None):
            vals=[None]+list(options);v=saved.get(key)
            if v not in vals:v=None
            value=st.selectbox(INPUT_LABELS.get(key,key),vals,index=vals.index(v),
                     format_func=lambda x:'Chưa thẩm định' if x is None else 'Có' if x is True else 'Không' if x is False else str(x),
                     key=f'ins_{ticker}_{key}',help=help)
            out[key]=value;return value
        out['ScopeConfirmed']=st.checkbox('Đã xác nhận pháp nhân và dữ liệu thuộc phạm vi phi nhân thọ',value=saved.get('ScopeConfirmed',False),key='scope_'+ticker)
        ev={}
        for group,items in RUBRIC.items():
            with st.expander(group):
                rows=[r for r in rubric_rows(saved.get('Evidence')) if r['Nhóm']==group]
                df=pd.DataFrame([{'Key':r['Key'],'Chỉ tiêu':r['Chỉ tiêu'],'Đánh giá':r['Đánh giá'],'Lập luận':r['Lập luận'],'Nguồn':r['Nguồn']} for r in rows])
                edited=st.data_editor(df,hide_index=True,use_container_width=True,disabled=['Key','Chỉ tiêu'],
                     column_config={'Key':None,'Đánh giá':st.column_config.SelectboxColumn(options=['Chưa thẩm định']+QUAL,required=True)},
                     key=f'ins_{ticker}_rubric_{group.split('.')[0]}')
                for row in edited.to_dict('records'):
                    ev[row['Key']]={'Assessment':row['Đánh giá'],'Reason':str(row['Lập luận'] or ''),'Source':str(row['Nguồn'] or '')}
                for _,label,rule in items:st.caption(label+': '+rule)
        out['Evidence']=ev
        st.markdown('**Điểm tổng hợp và giới hạn**')
        out['LicenseWithdrawal']=st.checkbox('Áp dụng ngoại lệ thu hồi giấy phép đã có quyết định Hội đồng',value=saved.get('LicenseWithdrawal',False),key=f'ins_{ticker}_license')
        if out['LicenseWithdrawal']:
            out['ExceptionSource']=st.text_area('Nguồn quyết định thu hồi giấy phép và quyết định Hội đồng',value=saved.get('ExceptionSource',''),key=f'ins_{ticker}_exception_source')
        for key,opts in [('MacroIndustryRisk',range(1,7)),('BusinessRisk',range(1,7)),('CapitalAdequacy',range(1,9)),
                         ('ModelRepresentativeness',['Tích cực','Trung lập','Tiêu cực vừa phải','Tiêu cực']),
                         ('RegulatoryRisk',['Thấp','Đáng kể']),('RiskPosition',range(1,6)),
                         ('FinancialAdjustment',range(-1,10)),('AssetQuality',['Trên BBB','BBB','BB','B+ trở xuống']),
                         ('InvestmentStress',[False,True]),('ManagementAssessment',GOV_LEVELS),('FinancialPolicyAssessment',GOV_LEVELS),
                         ('GovernanceHarmful',[False,True]),('LiquidityScore',range(1,6)),('LiquidityNotches',range(-8,1)),
                         ('OtherAdjustmentsNotches',range(-18,2) if out.get('LicenseWithdrawal') and out.get('ExceptionSource','').strip() else [-1,0,1]),('ComparativeNotches',[-1,0,1]),
                         ('GroupSupportNotches',range(19)),('GovernmentSupportNotches',range(19)),('ExternalSupportNotches',range(19))]:
            select(key,opts)
        st.caption('FinancialAdjustment là quyết định tổng hợp Bảng 11: mức 1/2/3/4 tương ứng −1/0/+1/+2; vị thế mức 5: +3 hoặc xấu hơn. Tài liệu không quy định phép gộp duy nhất khi hai yếu tố khác mức. Chất lượng tài sản nhập sau đánh giá đa dạng hóa; không tự nâng nguyên một nhóm hạng.')
        st.caption('Điều chỉnh thanh khoản: tài liệu không có bảng notch cơ học, cần quyết định có lập luận. Hỗ trợ ròng phải có hồ sơ phương pháp tập đoàn/Chính phủ riêng và loại trùng; không tự cộng hai nguồn.')
        for key in ['DecisionReason','SupportSource']:
            out[key]=st.text_area(INPUT_LABELS[key],value=saved.get(key,''),key=f'ins_{ticker}_{key}')
        # Hai lựa chọn phụ chỉ xuất hiện khi ô ma trận yêu cầu.
        candidate=insurance_rating(ticker,out)
        if isinstance(candidate.get('CombinedRiskCandidates'),tuple):
            select('CombinedRiskSelection',candidate['CombinedRiskCandidates'])
            candidate=insurance_rating(ticker,out)
        choices=anchor_options(candidate)
        if choices:select('AnchorSelection',choices)
        st.session_state[saved_key]=out
        st.download_button('Tải phiếu thẩm định đã nhập (JSON)',json.dumps(out,ensure_ascii=False,indent=2),ticker+'_insurance_assessment.json','application/json',key='ins_draft_'+ticker)
    return out
