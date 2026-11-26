"""
결(GYEOL) - 한국 시장 특화 고품질 슬라이드 및 디자인 프리셋 라이브러리
"""

PRESET_CATEGORIES = [
    {
        "id": "pitch-deck",
        "title": "스타트업 IR 피치덱 (투자유치)",
        "badge": "투자 / IR",
        "desc": "문제 제기부터 솔루션, 시장 규모(TAM/SAM/SOM), 비즈니스 모델, 성장 지표, 팀 소개까지 투자자를 사로잡는 정석 피치덱",
        "theme": "pitch-deck-vc",
        "font": "gmarket",
        "slides_count": 8,
        "default_prompt": "AI 기반 B2B 업무 자동화 솔루션 '오토웍스(AutoWorks)'의 시드 투자유치를 위한 IR 피치덱을 작성해줘.",
        "sample_html": """
  <!-- 1. 표지 -->
  <section class="slide" data-title="표지">
    <div class="kicker">Seed Round · 2026</div>
    <h1 class="h1 anim-fade-up" data-anim="fade-up">반복 업무의 90%를 없애는<br><span class="gradient-text">지능형 워크플로우 OS</span></h1>
    <p class="lede mt-m">국내 700만 소상공인과 중소기업을 위한 노코드 AI 업무 자동화 솔루션, <strong>오토웍스(AutoWorks)</strong></p>
    <div style="margin-top: 40px; display: flex; gap: 16px;">
      <span class="pill pill-accent">IR 피치덱</span>
      <span class="pill">2026년 상반기</span>
    </div>
    <aside class="notes">
      안녕하세요. 반복 업무를 원클릭으로 자동화하는 오토웍스 대표 홍길동입니다.
      오늘 저희가 어떻게 중소기업의 비효율을 해결하고 새로운 시장을 창출하는지 말씀드리겠습니다.
    </aside>
  </section>

  <!-- 2. 문제 정의 -->
  <section class="slide" data-title="문제 정의">
    <span class="kicker">01 · PROBLEM</span>
    <h2 class="h2 mt-s">하루 3시간 이상을<br>단순 복사·붙여넣기에 낭비하고 있습니다.</h2>
    <div class="grid g3 mt-l">
      <div class="card card-hover">
        <h4>파편화된 툴</h4>
        <p class="dim">ERP, 엑셀, 이메일, 카카오톡 채널 등 5개 이상의 시스템이 서로 연결되지 않고 단절되어 있습니다.</p>
      </div>
      <div class="card card-hover">
        <h4>월 120만 원 인건비 낭비</h4>
        <p class="dim">직원 1인당 매달 60시간 이상을 단순 송장 입력, 데이터 정리, 재고 확인에 소모합니다.</p>
      </div>
      <div class="card card-hover">
        <h4>휴먼 에러 14.8%</h4>
        <p class="dim">수기 입력 과정에서 발생하는 오입력으로 인해 매월 수백만 원의 정산 오차가 발생합니다.</p>
      </div>
    </div>
    <aside class="notes">
      실제 중소기업 실무진 200명을 심층 인터뷰한 결과, 놀랍게도 하루 평균 3시간 이상을 단순 작업에 쓰고 있었습니다.
      이 문제를 해결하지 못하면 성장은 불가능합니다.
    </aside>
  </section>

  <!-- 3. 솔루션 -->
  <section class="slide" data-title="솔루션">
    <span class="kicker">02 · SOLUTION</span>
    <h2 class="h2 mt-s">오토웍스는 업무의 모든 과정을<br><span class="gradient-text">단 하나의 파이프라인</span>으로 묶습니다.</h2>
    <p class="lede mt-m">주문 접수부터 결제 확인, 고객 알림톡 발송, ERP 재고 반영까지 사람이 손대지 않아도 100% 자율 실행됩니다.</p>
    <div class="row mt-l wrap">
      <span class="pill pill-accent">스마트 주문 연동</span>
      <span class="pill pill-accent">자동 세금계산서 발행</span>
      <span class="pill pill-accent">AI CS 챗봇</span>
      <span class="pill pill-accent">실시간 재고 추적</span>
      <span class="pill pill-accent">원클릭 리포트</span>
    </div>
    <aside class="notes">
      오토웍스는 기존 툴들을 교체할 필요 없이, API와 AI 에이전트를 통해 기존 시스템 위에 매끄럽게 얹어지는 솔루션입니다.
    </aside>
  </section>

  <!-- 4. 시장 규모 -->
  <section class="slide" data-title="시장 규모">
    <span class="kicker">03 · MARKET SIZE</span>
    <h2 class="h2 mt-s">연평균 24.5% 고속 성장하는<br>국내외 B2B SaaS 시장</h2>
    <div class="grid g3 mt-l">
      <div class="card">
        <p class="kicker">TAM (전체 시장)</p>
        <h1 class="h1" style="font-size: 54px; margin: 10px 0;">12.4조</h1>
        <p class="dim">국내 중소기업 및 소상공인 디지털 전환 솔루션 전체 시장</p>
      </div>
      <div class="card" style="border-top: 3px solid var(--accent);">
        <p class="kicker">SAM (유효 시장)</p>
        <h1 class="h1" style="font-size: 54px; margin: 10px 0; color: var(--accent);">3.8조</h1>
        <p class="dim">이커머스 및 유통/물류 기반 자동화 솔루션 도입 잠재 기업</p>
      </div>
      <div class="card">
        <p class="kicker">SOM (수익 시장)</p>
        <h1 class="h1" style="font-size: 54px; margin: 10px 0;">4,500억</h1>
        <p class="dim">향후 3년 내 오토웍스가 최우선 점유 가능한 초기 타깃 시장</p>
      </div>
    </div>
    <aside class="notes">
      국내 시장만 해도 유효 시장이 3.8조 원에 달하며, 특히 이커머스 셀러와 풀필먼트 기업들의 수요가 매우 폭발적입니다.
    </aside>
  </section>

  <!-- 5. 비즈니스 모델 -->
  <section class="slide" data-title="비즈니스 모델">
    <span class="kicker">04 · BUSINESS MODEL</span>
    <h2 class="h2 mt-s">월간 구독(MRR) + 사용량 기반 트랜잭션 과금</h2>
    <div class="grid g3 mt-l">
      <div class="card card-soft">
        <h3>스타터 (Starter)</h3>
        <h2 class="mt-s" style="color: var(--accent);">월 4.9만 원</h2>
        <p class="dim mt-m">월 자동화 건수 3,000건<br>기본 템플릿 20종 제공<br>이메일/슬랙 연동</p>
      </div>
      <div class="card" style="border: 2px solid var(--accent);">
        <span class="pill pill-accent" style="margin-bottom: 8px;">가장 인기</span>
        <h3>프로 (Pro)</h3>
        <h2 class="mt-s" style="color: var(--accent);">월 14.9만 원</h2>
        <p class="dim mt-m">월 자동화 30,000건<br>전용 ERP 커스텀 연동<br>24시간 우선 기술 지원</p>
      </div>
      <div class="card card-soft">
        <h3>엔터프라이즈</h3>
        <h2 class="mt-s" style="color: var(--accent);">맞춤 견적</h2>
        <p class="dim mt-m">무제한 트랜잭션<br>온프레미스 / 전용 클라우드<br>전담 엔지니어 배정</p>
      </div>
    </div>
    <aside class="notes">
      진입 장벽을 낮춘 스타터 플랜으로 빠른 락인을 유도하고, 사용량이 늘어날수록 객단가가 자연스럽게 증가하는 과금 체계입니다.
    </aside>
  </section>

  <!-- 6. 핵심 팀원 -->
  <section class="slide" data-title="팀 소개">
    <span class="kicker">05 · TEAM</span>
    <h2 class="h2 mt-s">B2B SaaS 엑싯 경험과<br>AI 기술력을 겸비한 드림팀</h2>
    <div class="grid g3 mt-l">
      <div class="card">
        <h4>홍길동 · 대표 (CEO)</h4>
        <p class="kicker" style="font-size: 13px;">연쇄 창업가 & Ex-쿠팡 PO</p>
        <p class="dim mt-s">전 B2B 플랫폼 창업 후 M&A 성공 엑싯 경험 보유. 10년간 이커머스 운영 최적화 지휘.</p>
      </div>
      <div class="card">
        <h4>김철수 · 기술이사 (CTO)</h4>
        <p class="kicker" style="font-size: 13px;">Ex-네이버 AI 엔지니어</p>
        <p class="dim mt-s">대규모 분산 트래픽 아키텍처 및 LLM 파이프라인 연구 8년. 시스템 안정성 99.99% 보장.</p>
      </div>
      <div class="card">
        <h4>이영희 · 사업총괄 (COO)</h4>
        <p class="kicker" style="font-size: 13px;">Ex-토스 비즈니스 리드</p>
        <p class="dim mt-s">초기 B2B 영업 200건 달성 및 전략 파트너십 총괄. 연간 리텐션율 94% 달성.</p>
      </div>
    </div>
    <aside class="notes">
      저희 팀은 이미 동종 업계에서 창업과 엑싯을 성공적으로 경험한 멤버들로 결성되어 최고의 실행력을 자신합니다.
    </aside>
  </section>

  <!-- 7. 성장 지표 -->
  <section class="slide" data-title="트랙션">
    <span class="kicker">06 · TRACTION</span>
    <h2 class="h2 mt-s">베타 오픈 3개월 만에 입증된<br><span class="gradient-text">폭발적인 PMF와 시장 반응</span></h2>
    <div class="grid g4 mt-l">
      <div class="card center">
        <p class="dim">유료 기업 고객</p>
        <h1 class="h1 mt-s" style="color: var(--accent); font-size: 48px;">180+</h1>
        <p class="kicker" style="font-size: 12px;">전월 대비 +140%</p>
      </div>
      <div class="card center">
        <p class="dim">월간 반복 매출 (MRR)</p>
        <h1 class="h1 mt-s" style="color: var(--good); font-size: 48px;">4,200만</h1>
        <p class="kicker" style="font-size: 12px;">BEP 조기 달성 전망</p>
      </div>
      <div class="card center">
        <p class="dim">월간 리텐션</p>
        <h1 class="h1 mt-s" style="color: var(--accent); font-size: 48px;">96.4%</h1>
        <p class="kicker" style="font-size: 12px;">업계 최상위 수준</p>
      </div>
      <div class="card center">
        <p class="dim">누적 처리 건수</p>
        <h1 class="h1 mt-s" style="color: var(--accent); font-size: 48px;">1,200만</h1>
        <p class="kicker" style="font-size: 12px;">무장애 운영</p>
      </div>
    </div>
    <aside class="notes">
      출시 3개월 만에 180개 이상의 유료 기업 고객을 확보했으며, 리텐션율 96.4%로 고객들이 서비스를 떠나지 않고 있습니다.
    </aside>
  </section>

  <!-- 8. 마무리 -->
  <section class="slide" data-title="비전 및 마무리">
    <div class="kicker">THE FUTURE OF WORK</div>
    <h1 class="h1 anim-fade-up" data-anim="fade-up">모든 기업이 핵심에만 집중하는 세상,<br><span class="gradient-text">오토웍스와 함께 만들어가십시오.</span></h1>
    <p class="lede mt-m">이번 시드 라운드를 통해 인재 영입 및 엔터프라이즈 모듈 확장을 가속화합니다.</p>
    <div class="card mt-l" style="max-width: 450px;">
      <h4>투자 및 협업 문의</h4>
      <p class="dim mt-s">이메일: contact@autoworks.kr<br>홈페이지: https://autoworks.kr</p>
    </div>
    <aside class="notes">
      경청해 주셔서 대단히 감사합니다. 질문해 주시면 상세히 답변드리겠습니다.
    </aside>
  </section>
"""
    },
    {
        "id": "business-proposal",
        "title": "비즈니스 사업 제안서",
        "badge": "제안 / 영업",
        "desc": "고객사의 니즈 분석, 솔루션 제시, 구축 범위(WBS), 투입 공수, 기대 효과를 논리정연하게 설득하는 상업용 제안서",
        "theme": "corporate-clean",
        "font": "pretendard",
        "slides_count": 6,
        "default_prompt": "제조 기업을 위한 '스마트 팩토리 IoT 데이터 분석 시스템 구축' 사업 제안서를 작성해줘.",
        "sample_html": """
  <!-- 1. 표지 -->
  <section class="slide" data-title="표지">
    <div class="kicker">Business Proposal</div>
    <h1 class="h1 anim-fade-up" data-anim="fade-up">스마트 팩토리 IoT 데이터 분석 시스템<br><span class="gradient-text">통합 구축 사업 제안서</span></h1>
    <p class="lede mt-m">실시간 생산 공정 모니터링 및 AI 예지보전 솔루션을 통한 생산성 25% 향상 방안</p>
    <div class="deck-footer">
      <span>제안사: (주)스마트데이터랩스</span>
      <span>2026. 10</span>
    </div>
    <aside class="notes">
      귀사의 스마트 팩토리 고도화를 위한 제안 발표를 맡게 된 스마트데이터랩스 사업본부장입니다.
    </aside>
  </section>

  <!-- 2. 제안 배경 및 니즈 -->
  <section class="slide" data-title="제안 배경">
    <span class="kicker">01 · BACKGROUND</span>
    <h2 class="h2 mt-s">귀사의 현재 제조 공정 핵심 과제</h2>
    <div class="grid g2 mt-l">
      <div class="card">
        <h4>설비 고장으로 인한 다운타임</h4>
        <p class="dim">예상치 못한 기계 고장으로 연간 120시간 이상의 라인 정지가 발생하여 막대한 납기 지연 손실 초래.</p>
      </div>
      <div class="card">
        <h4>작업자 숙련도 편차</h4>
        <p class="dim">품질 검사 및 수치 조정이 베테랑 작업자의 감에 의존하여 공정 간 불량률 편차 발생.</p>
      </div>
    </div>
    <aside class="notes">
      사전 현장 실사를 통해 확인한 결과, 라인 정지로 인한 손실이 매년 수억 원에 달하고 있었습니다.
    </aside>
  </section>

  <!-- 3. 핵심 제안 내용 -->
  <section class="slide" data-title="제안 솔루션">
    <span class="kicker">02 · PROPOSED SOLUTION</span>
    <h2 class="h2 mt-s">3단계 IoT + AI 실시간 통합 예지보전 체계</h2>
    <div class="grid g3 mt-l">
      <div class="card card-soft">
        <h3>Step 1. 센서 수집</h3>
        <p class="dim mt-s">진동, 온도, 전력 등 초당 1,000회 진동 감지 무선 센서 부착</p>
      </div>
      <div class="card card-soft">
        <h3>Step 2. AI 이상 감지</h3>
        <p class="dim mt-s">사전 학습된 딥러닝 모델이 이상 징후를 고장 48시간 전 자동 감지</p>
      </div>
      <div class="card card-soft">
        <h3>Step 3. 통합 관제</h3>
        <p class="dim mt-s">현장 태블릿 및 중앙 대시보드로 실시간 설비 헬스 스코어 시각화</p>
      </div>
    </div>
    <aside class="notes">
      단순 모니터링이 아닌, 고장이 나기 48시간 전에 알람을 주는 예지보전 시스템이 핵심입니다.
    </aside>
  </section>

  <!-- 4. 구축 일정 및 WBS -->
  <section class="slide" data-title="추진 일정">
    <span class="kicker">03 · TIMELINE</span>
    <h2 class="h2 mt-s">총 12주 완성형 단계별 구축 로드맵</h2>
    <div class="grid g4 mt-l">
      <div class="card">
        <h4>1~2주차</h4>
        <p class="dim">요구사항 상세 정의 및 현장 통신 환경 실사</p>
      </div>
      <div class="card">
        <h4>3~6주차</h4>
        <p class="dim">IoT 게이트웨이 설치 및 데이터 파이프라인 개발</p>
      </div>
      <div class="card">
        <h4>7~10주차</h4>
        <p class="dim">AI 모델 커스텀 튜닝 및 관제 웹 UI 연동</p>
      </div>
      <div class="card">
        <h4>11~12주차</h4>
        <p class="dim">현장 파일럿 테스트 및 작업자 운영 교육</p>
      </div>
    </div>
    <aside class="notes">
      체계적인 12주 스프린트를 통해 기존 공정 가동을 중단하지 않고 설치를 완료합니다.
    </aside>
  </section>

  <!-- 5. 기대 효과 -->
  <section class="slide" data-title="기대 효과">
    <span class="kicker">04 · EXPECTED OUTCOME</span>
    <h2 class="h2 mt-s">도입 즉시 실현되는 3대 정량적 성과</h2>
    <div class="grid g3 mt-l">
      <div class="card center">
        <h1 class="h1" style="color: var(--good); font-size: 56px;">▼ 72%</h1>
        <h4>설비 고장 다운타임 감소</h4>
        <p class="dim">돌발 가동 중단 연간 120시간 → 34시간 감축</p>
      </div>
      <div class="card center">
        <h1 class="h1" style="color: var(--accent); font-size: 56px;">▲ 25%</h1>
        <h4>라인 생산성 향상</h4>
        <p class="dim">시간당 부품 생산량 420개 → 525개 증대</p>
      </div>
      <div class="card center">
        <h1 class="h1" style="color: var(--warn); font-size: 56px;">3.4개월</h1>
        <h4>투자비용 회수 기간 (ROI)</h4>
        <p class="dim">도입 첫해 순비용 절감액 약 2.4억 원 예상</p>
      </div>
    </div>
    <aside class="notes">
      도입 후 4개월 이내에 투자 비용 전액을 회수할 수 있을 만큼 확실한 ROI를 보장합니다.
    </aside>
  </section>

  <!-- 6. 마무리 -->
  <section class="slide" data-title="맺음말">
    <div class="kicker">THANK YOU</div>
    <h1 class="h1 anim-fade-up" data-anim="fade-up">귀사의 성공적인 디지털 혁신,<br><span class="gradient-text">신뢰할 수 있는 파트너와 함께하십시오.</span></h1>
    <p class="lede mt-m">검증된 레퍼런스와 기술력으로 프로젝트의 완벽한 성공을 약속드립니다.</p>
    <div class="card mt-l" style="max-width: 400px;">
      <h4>프로젝트 총괄 PM</h4>
      <p class="dim mt-s">사업본부 김수석 이사 (010-1234-5678)<br>Email: proposal@example.com</p>
    </div>
    <aside class="notes">
      귀사와의 훌륭한 파트너십을 기대합니다. 경청해 주셔서 감사합니다.
    </aside>
  </section>
"""
    },
    {
        "id": "tech-sharing",
        "title": "개발자 테크 세미나 & 아키텍처 발표",
        "badge": "기술 / 개발",
        "desc": "시스템 구조도, 기술 스택 비교, 코드 블록 및 트러블슈팅 사례를 명확하게 전달하는 엔지니어링 발표 슬라이드",
        "theme": "g001",
        "font": "spoqa",
        "slides_count": 6,
        "default_prompt": "초당 10만 건 트래픽을 처리하는 '대규모 실시간 이벤트 브로커 아키텍처 전환기' 발표 슬라이드를 작성해줘.",
        "sample_html": """
  <!-- 1. 표지 -->
  <section class="slide" data-title="표지">
    <div class="kicker">TECH TALK · 2026</div>
    <h1 class="h1 anim-fade-up" data-anim="fade-up">초당 10만 건 트래픽을 버텨낸<br><span class="gradient-text">이벤트 브로커 아키텍처 전환기</span></h1>
    <p class="lede mt-m">모놀리식 RDB 병목에서 Kafka + Redis 클러스터 비동기 파이프라인으로의 6개월 여정</p>
    <div class="row mt-l">
      <span class="pill pill-accent">백엔드 아키텍처</span>
      <span class="pill">Kafka</span>
      <span class="pill">Redis</span>
      <span class="pill">Kubernetes</span>
    </div>
    <aside class="notes">
      안녕하세요. 백엔드 플랫폼팀 리드 김개발입니다. 오늘 공유할 주제는 대규모 트래픽 분산 아키텍처 전환기입니다.
    </aside>
  </section>

  <!-- 2. 기존 문제점 -->
  <section class="slide" data-title="기존 문제점">
    <span class="kicker">01 · BOTTLENECK</span>
    <h2 class="h2 mt-s">트래픽 급증 시 발생한 3대 장애 패턴</h2>
    <div class="grid g3 mt-l">
      <div class="card">
        <h4>DB 커넥션 풀 고갈</h4>
        <p class="dim">이벤트 발생 시 동기식 트랜잭션으로 인해 DB Pool 1,000개가 2초 만에 소진.</p>
      </div>
      <div class="card">
        <h4>캐스케이딩 타임아웃</h4>
        <p class="dim">선행 API 응답 지연이 하위 마이크로서비스 전반으로 전파되어 연쇄 장애 유발.</p>
      </div>
      <div class="card">
        <h4>데이터 정합성 훼손</h4>
        <p class="dim">재시도(Retry) 폭풍으로 인한 중복 이벤트 처리 및 결제 상태 불일치 발생.</p>
      </div>
    </div>
    <aside class="notes">
      작년 대규모 할인 이벤트 때 동기식 호출 구조 때문에 전사 장애를 겪었습니다.
    </aside>
  </section>

  <!-- 3. 신규 아키텍처 -->
  <section class="slide" data-title="신규 아키텍처">
    <span class="kicker">02 · NEW ARCHITECTURE</span>
    <h2 class="h2 mt-s">Event-Driven 비동기 디커플링</h2>
    <div class="grid g2 mt-l">
      <div class="card">
        <h4>1. 엣지 레이어 (Edge Layer)</h4>
        <p class="dim">Nginx 인그레스에서 들어오는 요청을 메모리 버퍼에 즉시 큐잉 후 HTTP 202 Accepted 반환.</p>
      </div>
      <div class="card">
        <h4>2. 카프카 파티셔닝 (Kafka Partitioning)</h4>
        <p class="dim">고객 식별자 해시 기반으로 64개 파티션에 균등 분산하여 메시지 순서성 보장.</p>
      </div>
    </div>
    <aside class="notes">
      핵심은 클라이언트에게 즉시 접수 응답을 주고, 뒤단에서 파티셔닝된 카프카 워커가 안정적으로 소비하는 것입니다.
    </aside>
  </section>

  <!-- 4. 성능 개선 결과 -->
  <section class="slide" data-title="성능 지표">
    <span class="kicker">03 · BENCHMARK</span>
    <h2 class="h2 mt-s">전환 전후 성능 벤치마크 결과</h2>
    <div class="grid g3 mt-l">
      <div class="card center">
        <p class="dim">P99 응답 시간</p>
        <h1 class="h1" style="color: var(--good); font-size: 52px;">820ms → 18ms</h1>
        <p class="kicker" style="font-size: 13px;">97.8% 지연시간 단축</p>
      </div>
      <div class="card center">
        <p class="dim">초당 처리량 (Throughput)</p>
        <h1 class="h1" style="color: var(--accent); font-size: 52px;">12.5배 ▲</h1>
        <p class="kicker" style="font-size: 13px;">최대 115,000 TPS 기록</p>
      </div>
      <div class="card center">
        <p class="dim">인프라 월 비용</p>
        <h1 class="h1" style="color: var(--good); font-size: 52px;">40% 절감</h1>
        <p class="kicker" style="font-size: 13px;">DB 스케일업 비용 해소</p>
      </div>
    </div>
    <aside class="notes">
      P99 응답 속도가 800ms대에서 10ms대로 극적으로 줄어들었으며 인프라 비용도 40% 절감되었습니다.
    </aside>
  </section>

  <!-- 5. 얻은 교훈 -->
  <section class="slide" data-title="회고 및 레슨">
    <span class="kicker">04 · RETROSPECTIVE</span>
    <h2 class="h2 mt-s">엔지니어링 팀이 얻은 3가지 핵심 레슨</h2>
    <div class="grid g3 mt-l">
      <div class="card card-soft">
        <h4>멱등성(Idempotency) 설계 필수</h4>
        <p class="dim">모든 컨슈머는 최소 1회(At-least-once) 전송 환경에서 중복 처리를 자체 방어해야 합니다.</p>
      </div>
      <div class="card card-soft">
        <h4>DLQ(Dead Letter Queue) 구축</h4>
        <p class="dim">비정상 페이로드가 전체 파티션을 블로킹하지 않도록 격리 큐를 즉시 분리해야 합니다.</p>
      </div>
      <div class="card card-soft">
        <h4>메트릭 시각화 & 알람</h4>
        <p class="dim">Consumer Lag 모니터링이 지연 발생 감지의 최우선 지표였습니다.</p>
      </div>
    </div>
    <aside class="notes">
      이벤트 기반 시스템에서는 무엇보다 멱등성 보장이 첫 단추입니다.
    </aside>
  </section>

  <!-- 6. Q&A -->
  <section class="slide" data-title="질의응답">
    <div class="kicker">Q & A</div>
    <h1 class="h1 anim-fade-up" data-anim="fade-up">질문과 토론을 환영합니다</h1>
    <p class="lede mt-m">사내 위키에서 상세 아키텍처 다이어그램과 소스 코드를 확인하실 수 있습니다.</p>
    <div class="card mt-l" style="max-width: 400px;">
      <p class="dim">GitHub: github.com/team/event-broker<br>기술 블로그: tech.company.io</p>
    </div>
    <aside class="notes">
      오늘 공유드린 내용 중 궁금하신 점 편하게 질문 주시기 바랍니다.
    </aside>
  </section>
"""
    },
    {
        "id": "weekly-report",
        "title": "주간 / 월간 비즈니스 성과 보고서",
        "badge": "보고서 / 회의",
        "desc": "금주 핵심 성과(Done), 진행 중인 프로젝트(In Progress), 차주 계획(Next), 리스크 및 요청 사항을 깔끔하게 정리하는 보고 템플릿",
        "theme": "swiss-grid",
        "font": "nanum_neo",
        "slides_count": 5,
        "default_prompt": "마케팅 & 영업팀의 '2026년 3분기 성과 결산 및 4분기 실행 전략' 주간 보고 슬라이드를 작성해줘.",
        "sample_html": """
  <!-- 1. 표지 -->
  <section class="slide" data-title="표지">
    <div class="kicker">WEEKLY REPORT · 2026년 42주차</div>
    <h1 class="h1 anim-fade-up" data-anim="fade-up">3분기 마케팅 성과 결산 및<br><span class="gradient-text">4분기 핵심 실행 전략</span></h1>
    <p class="lede mt-m">신규 유입 140% 달성 현황 및 연말 블랙프라이데이 프로모션 계획</p>
    <div class="deck-footer">
      <span>보고자: 그로스마케팅팀</span>
      <span>2026. 10. 22</span>
    </div>
    <aside class="notes">
      이번 주 주간 보고는 3분기 마케팅 지표 결산과 다음 주부터 시작될 연말 캠페인 안건입니다.
    </aside>
  </section>

  <!-- 2. 금주 핵심 성과 -->
  <section class="slide" data-title="핵심 성과">
    <span class="kicker">01 · KEY ACHIEVEMENTS</span>
    <h2 class="h2 mt-s">3분기 목표 지표 초과 달성 현황</h2>
    <div class="grid g3 mt-l">
      <div class="card">
        <p class="kicker">신규 가입자 수</p>
        <h1 class="h1" style="color: var(--good); font-size: 52px;">48,200명</h1>
        <p class="dim">목표 대비 114% 달성 (YoY +68%)</p>
      </div>
      <div class="card">
        <p class="kicker">CAC (고객 획득 비용)</p>
        <h1 class="h1" style="color: var(--accent); font-size: 52px;">8,400원</h1>
        <p class="dim">전 분기 대비 22% 단축 (효율 극대화)</p>
      </div>
      <div class="card">
        <p class="kicker">ROAS (광고 수익률)</p>
        <h1 class="h1" style="color: var(--good); font-size: 52px;">430%</h1>
        <p class="dim">퍼포먼스 캠페인 소재 최적화 성공</p>
      </div>
    </div>
    <aside class="notes">
      소재 A/B 테스트를 80회 이상 집중 실행하여 획득 단가를 8천 원대로 낮춘 것이 주효했습니다.
    </aside>
  </section>

  <!-- 3. 진행 중인 과제 -->
  <section class="slide" data-title="진행 현황">
    <span class="kicker">02 · IN PROGRESS</span>
    <h2 class="h2 mt-s">연말 대규모 프로모션 준비 진척도</h2>
    <div class="grid g2 mt-l">
      <div class="card card-soft">
        <h4>1. 블랙프라이데이 티징 페이지 오픈</h4>
        <p class="kicker" style="font-size: 13px;">진행률 85% · 10월 28일 배포 예정</p>
        <p class="dim mt-s">사전 예약자 대상 한정 할인 쿠폰팩 발송 시스템 검수 완료.</p>
      </div>
      <div class="card card-soft">
        <h4>2. 인플루언서 제휴 영상 12편 제작</h4>
        <p class="kicker" style="font-size: 13px;">진행률 70% · 최종 편집 단계</p>
        <p class="dim mt-s">유튜브 및 릴스 메인 채널 6곳 최종 컨펌 완료, 11월 1일 일괄 온에어.</p>
      </div>
    </div>
    <aside class="notes">
      티징 페이지는 디자인과 퍼블리싱이 마무리되었고 결제 연동 테스트 중입니다.
    </aside>
  </section>

  <!-- 4. 이슈 및 지원 요청 -->
  <section class="slide" data-title="이슈 및 리스크">
    <span class="kicker">03 · BLOCKERS & REQUESTS</span>
    <h2 class="h2 mt-s">의사결정이 필요한 주요 안건</h2>
    <div class="grid g2 mt-l">
      <div class="card" style="border-left: 4px solid var(--bad);">
        <h4>트래픽 급증 대비 서버 증설 승인 건</h4>
        <p class="dim">프로모션 당일 동시 접속자 5만 명 예상 → AWS 오토스케일링 예산 250만 원 추가 승인 요청.</p>
      </div>
      <div class="card" style="border-left: 4px solid var(--warn);">
        <h4>CS 응대 인력 단기 충원 건</h4>
        <p class="dim">행사 기간 1주일간 카카오톡 상담 봇 외 전문 상담원 파트타임 2인 배치 협의 필요.</p>
      </div>
    </div>
    <aside class="notes">
      서버 부하와 CS 지연을 방지하기 위해 예산 승인과 인력 지원을 요청드립니다.
    </aside>
  </section>

  <!-- 5. 차주 일정 -->
  <section class="slide" data-title="차주 계획">
    <span class="kicker">04 · NEXT STEPS</span>
    <h2 class="h2 mt-s">다음 주 핵심 마일스톤</h2>
    <div class="grid g3 mt-l">
      <div class="card">
        <h4>월요일</h4>
        <p class="dim">사전 예약 티징 랜딩페이지 최종 QA 및 오픈</p>
      </div>
      <div class="card">
        <h4>수요일</h4>
        <p class="dim">전체 회원 대상 얼리버드 알림톡 1차 발송</p>
      </div>
      <div class="card">
        <h4>금요일</h4>
        <p class="dim">사전 등록 1만 명 돌파 현황 점검 및 본 행사 라이브</p>
      </div>
    </div>
    <aside class="notes">
      다음 주 월요일 오픈 후 지표를 매일 오전 슬랙으로 공유해 드리겠습니다. 감사합니다.
    </aside>
  </section>
"""
    }
]


def get_all_presets():
    """모든 프리셋 목록을 반환합니다."""
    return [
        {
            "id": p["id"],
            "title": p["title"],
            "badge": p["badge"],
            "desc": p["desc"],
            "theme": p["theme"],
            "font": p["font"],
            "slides_count": p["slides_count"],
            "default_prompt": p["default_prompt"],
        }
        for p in PRESET_CATEGORIES
    ]


def get_preset_by_id(preset_id: str):
    """특정 ID의 프리셋을 반환합니다."""
    for p in PRESET_CATEGORIES:
        if p["id"] == preset_id:
            return p
    return PRESET_CATEGORIES[0]
