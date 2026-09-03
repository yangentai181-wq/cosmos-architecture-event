from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Day2CloseoutDocsTest(unittest.TestCase):
    def read(self, relative_path):
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_closeout_points_to_all_unsent_external_gates(self):
        closeout = self.read("docs/day2-closeout-2026-09-04.md")
        self.assertIn("土地0でも7%上限超過", closeout)
        for reference in (
            "docs/ibaraki-preconsultation-sheet-2026-09-04.md",
            "docs/oic-dorm-data-request-draft-2026-09-04.md",
            "docs/operator-quote-request-draft-2026-09-04.md",
            "docs/price-positioning-and-demand-gate-2026-09-04.md",
        ):
            self.assertIn(reference, closeout)
            self.assertTrue((ROOT / reference).exists())

        city = self.read("docs/ibaraki-preconsultation-sheet-2026-09-04.md")
        oic = self.read("docs/oic-dorm-data-request-draft-2026-09-04.md")
        self.assertIn("2026年9月4日に市公式ページ", city)
        self.assertIn("審査指導課", city)
        self.assertIn("2026年9月4日にI-House・G-House各公式ページ", oic)

    def test_price_gate_distinguishes_total_cost_from_rent(self):
        price_gate = self.read("docs/price-positioning-and-demand-gate-2026-09-04.md")
        for phrase in (
            "月額総費用",
            "約10万5,700〜11万7,700円",
            "7%必要家賃173,162円",
            "7%必要家賃189,047〜193,719円",
            "19万円以上",
            "実際の決済・個人情報取得・外部公開は承認後",
        ):
            self.assertIn(phrase, price_gate)

    def test_operator_request_is_a_draft_with_itemized_costs(self):
        request = self.read("docs/operator-quote-request-draft-2026-09-04.md")
        self.assertIn("送信前ドラフト", request)
        self.assertIn("寄宿舎型84〜91室", request)
        self.assertIn("共同住宅型99戸", request)
        self.assertIn("売上歩合と分母", request)
        self.assertIn("食事なし・夜間オンコール", request)

    def test_ihouse_known_minimum_matches_officially_listed_fees(self):
        comparison = self.read("docs/annual-total-cost-comparison-2026-09-04.md")
        self.assertIn("既知最低84万5,400円", comparison)
        self.assertNotIn("既知最低84万4,600円", comparison)
        self.assertIn("契約事務手数料1万円", comparison)

    def test_tenant_income_is_treated_as_net_income_not_sales(self):
        tenant_gate = self.read("docs/tenant-lease-economics-gate-2026-09-04.md")
        for phrase in (
            "所有者純収入",
            "4,395.7万円",
            "7,431.4万円",
            "付帯事業利益0円",
            "条件書または未送信LOI案",
        ):
            self.assertIn(phrase, tenant_gate)

    def test_old_demand_package_warns_before_old_figures(self):
        package = self.read("docs/demand-validation-package-2026-09-03.md")
        first_twenty_lines = "\n".join(package.splitlines()[:20])
        self.assertIn("100ペア室・200人案は旧比較", first_twenty_lines)
        self.assertIn("docs/day2-closeout-2026-09-04.md", first_twenty_lines)

    def test_qa_keeps_upper_bound_and_feasible_range_separate(self):
        qa = self.read("docs/day2-questions-and-answers-2026-09-04.md")
        for phrase in (
            "168室は収支上限",
            "84〜99室は行政確認前の比較幅",
            "実平面で確認していない",
            "家賃10万円は収支表の入力値",
            "所有者純収入",
            "外部への送信は宛先と開示範囲を確認してから",
        ):
            self.assertIn(phrase, qa)

        closeout = self.read("docs/day2-closeout-2026-09-04.md")
        morning = self.read("docs/morning-decision-pack-2026-09-04.md")
        for document in (closeout, morning):
            self.assertIn("docs/day2-questions-and-answers-2026-09-04.md", document)

    def test_seven_percent_bridge_shows_zero_land_is_not_enough(self):
        bridge = self.read("docs/seven-percent-capital-bridge-2026-09-04.md")
        for phrase in (
            "7%許容投資上限 = 現行条件の年間利益 ÷ 7%",
            "7,085.7万円",
            "3.82%",
            "土地を0円としても現在の建設費だけで7%の許容投資上限を超える",
            "-39,634.3万円",
            "投資判断・見積ではない",
        ):
            self.assertIn(phrase, bridge)

        current = self.read("docs/current-direction-2026-09-03.md")
        self.assertIn("共有Sheet「Day2判断表」の20〜46行", current)

    def test_construction_cost_gate_keeps_workbook_cost_separate_from_sent_inquiry(self):
        gate = self.read("docs/construction-cost-scope-gate-2026-09-04.md")
        for phrase in (
            "32.06万円/㎡",
            "36.47万円/㎡",
            "13.8%高い",
            "主体工事費＋建築設備工事費",
            "建築分野の全建設コスト平均を27〜31%上昇",
            "現行Masterの単価基準日が不明",
            "空欄は「未取得」であり、0円ではない",
            "正式見積・投資判断ではない",
            "非公開「建設費ゲート_0904」",
        ):
            self.assertIn(phrase, gate)

        estimate_request = self.read(
            "docs/construction-cost-estimate-request-draft-2026-09-04.md"
        )
        for phrase in (
            "2026年9月4日 07:24 JST",
            "送信済み",
            "寄宿舎型84〜91室",
            "共同住宅型99戸",
            "含む・一部・含まない・未確認",
            "大学・土地所有者から正式委任された事業化案件ではありません",
            "見積発注・委託契約ではない",
        ):
            self.assertIn(phrase, estimate_request)

        for relative_path in (
            "docs/current-direction-2026-09-03.md",
            "docs/morning-decision-pack-2026-09-04.md",
            "docs/day2-closeout-2026-09-04.md",
        ):
            document = self.read(relative_path)
            self.assertIn("docs/construction-cost-scope-gate-2026-09-04.md", document)
            self.assertIn("docs/construction-cost-estimate-request-draft-2026-09-04.md", document)

    def test_operator_candidates_are_comparable_without_claiming_authority(self):
        candidates = self.read("docs/operator-candidate-shortlist-2026-09-04.md")
        for phrase in (
            "ジェイ・エス・ビー",
            "学生情報センター（ナジック）",
            "共立メンテナンス",
            "同じ条件・同じ回答様式",
            "大学・土地所有者・事業者から正式委任を受けた案件ではない",
            "どの会社も収支前提へ直接採用しない",
            "2026年9月4日に3社の学生寮・学校寮・寮事業ページを再確認",
        ):
            self.assertIn(phrase, candidates)

        request = self.read("docs/operator-quote-request-draft-2026-09-04.md")
        self.assertIn("学生の建築設計演習", request)
        self.assertIn("大学・土地所有者から正式委任された事業化案件ではありません", request)
        self.assertIn("運営見積比較_0904", request)
        self.assertIn("運営見積比較_0904", candidates)

        current = self.read("docs/current-direction-2026-09-03.md")
        morning = self.read("docs/morning-decision-pack-2026-09-04.md")
        self.assertIn("運営見積比較_0904", current)
        self.assertIn("運営見積比較_0904", morning)

    def test_drawing_brief_keeps_b1_b2_comparable_and_unconfirmed(self):
        brief = self.read("docs/design-development-drawing-brief-2026-09-04.md")
        for phrase in (
            "同じ敷地図、同じ縮尺、84室、公開・緩衝165㎡",
            "敷地制約図",
            "配置比較図",
            "1階平面比較図",
            "街路側立面",
            "動線断面",
            "面積・室数照合表",
            "受入れ前の20項目",
            "外部利用者、居住者、搬入・ごみ、避難・消防",
            "未確認条件は図面上で「未確認」と表示",
            "168室を法規・実配置の成立案として表示する",
        ):
            self.assertIn(phrase, brief)

        current = self.read("docs/current-direction-2026-09-03.md")
        morning = self.read("docs/morning-decision-pack-2026-09-04.md")
        for document in (current, morning):
            self.assertIn("図面受入基準_0904", document)

    def test_event_pilot_turns_capacity_into_measured_design_inputs(self):
        protocol = self.read("docs/event-pilot-measurement-protocol-2026-09-04.md")
        for phrase in (
            "12人、18人、24人の三段階",
            "受付・待合",
            "可変ラウンジ",
            "交流キッチン",
            "居住者専用部への境界越え",
            "運営者の総稼働",
            "人件費を含む総費用",
            "6役割",
            "8外部費",
            "全項目が揃うまで",
            "すぐ面積を増やさない",
            "少なくとも同じ人数条件を二回再現",
            "未実施のプロトコル",
        ):
            self.assertIn(phrase, protocol)

        current = self.read("docs/current-direction-2026-09-03.md")
        morning = self.read("docs/morning-decision-pack-2026-09-04.md")
        for document in (current, morning):
            self.assertIn("イベント実証記録_0904", document)
            self.assertIn("イベント原価_0904", document)

        operating_plan = self.read("docs/community-program-operating-plan-2026-09-03.md")
        self.assertIn(
            "防災まち歩きは運営等を含む約25人、お互い食堂は居住者12人→招待制18人→外部実証24人として別に測る",
            operating_plan,
        )

    def test_final_script_keeps_claims_inside_the_evidence_boundary(self):
        script = self.read("docs/final-presentation-script-2026-09-04.md")
        for phrase in (
            "合計は約3分",
            "5・6・7階 × B1/B2の6案",
            "イベント12→18→24人",
            "根拠のない確定を止める",
            "言わない表現",
            "外部回答前は7%、テナント利益、室数を確定しません",
        ):
            self.assertIn(phrase, script)

        current = self.read("docs/current-direction-2026-09-03.md")
        morning = self.read("docs/morning-decision-pack-2026-09-04.md")
        self.assertIn("docs/final-presentation-script-2026-09-04.md", current)
        self.assertIn("docs/final-presentation-script-2026-09-04.md", morning)
        self.assertIn("最終5枚｜3分発表原稿", current)
        self.assertIn("最終5枚の3分原稿", morning)
        self.assertIn("深夜作業サマリー", current)
        self.assertIn("state.md", morning)
        self.assertIn("外部確認台帳_0904", current)
        self.assertIn("外部確認台帳_0904", morning)

    def test_facade_specifications_are_routed_to_the_shared_comparison_register(self):
        facade = self.read("docs/facade-operation-brief-2026-09-04.md")
        current = self.read("docs/current-direction-2026-09-03.md")
        morning = self.read("docs/morning-decision-pack-2026-09-04.md")
        for document in (facade, current, morning):
            self.assertIn("外観仕様比較_0904", document)
        self.assertIn("候補、性能、概算、清掃、更新・補修単位", facade)

    def test_current_direction_matches_the_final_five_slide_order(self):
        current = self.read("docs/current-direction-2026-09-03.md")
        self.assertIn("11枚目を学生ニーズ5点", current)
        self.assertIn("12枚目を競合と差別化仮説", current)
        self.assertIn("13枚目を5・6・7階 × B1/B2の6案比較", current)
        self.assertIn("14枚目を外観運用と事業条件", current)
        self.assertIn("最終15枚目を最終判断とチーム過程の締め", current)

    def test_latest_massing_review_is_integrated_into_current_entrypoints(self):
        review_path = "docs/spatial-massing-deep-dive-2026-09-04.md"
        self.assertTrue((ROOT / review_path).exists())

        for relative_path in (
            "README.md",
            "docs/current-direction-2026-09-03.md",
            "docs/morning-decision-pack-2026-09-04.md",
            "docs/day2-closeout-2026-09-04.md",
        ):
            document = self.read(relative_path)
            self.assertIn(review_path, document)
            self.assertIn("5・6・7階", document)
            self.assertIn("優位未確定", document)

        drawing_brief = self.read(
            "docs/design-development-drawing-brief-2026-09-04.md"
        )
        self.assertIn("5・6・7階 × B1/B2", drawing_brief)
        self.assertIn("6セル", drawing_brief)

    def test_superseded_concept_argument_does_not_present_supply_as_demand_proof(self):
        old_argument = self.read("docs/concept-rationale-2026-09-04.md")
        self.assertIn("旧論証案・参考資料", old_argument)
        self.assertIn("369室は供給・競合の確認値であり、新築需要の証拠ではない", old_argument)
        self.assertNotIn("需要が実在する証拠", old_argument)
        self.assertNotIn("2年目以降の学生は必ず外へ出る", old_argument)
        self.assertNotIn("大学横断で受け入れられるのは民間だけ", old_argument)

        meeting = self.read("docs/meeting-action-items-2026-09-03.md")
        benchmark = self.read("docs/mixed-dormitory-benchmark-2026-09-03.md")
        self.assertNotIn("約368室", meeting)
        self.assertNotIn("368室（168＋201室）", benchmark)
        self.assertIn("369室（168＋201室）", benchmark)


if __name__ == "__main__":
    unittest.main()
