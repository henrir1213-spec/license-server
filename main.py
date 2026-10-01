import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import requests
import uuid
import os

app = FastAPI()

# Supabase 접속 정보
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jnimnexbzjljtmjueytm.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

headers = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Resend API 키 설정
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

def send_email_resend(to_email: str, license_key: str, expire_date_str: str, plan_name: str = "3일 무료 체험"):
    """Resend API를 사용하여 라이선스 키 이메일 발송"""
    resend_url = "https://api.resend.com/emails"
    email_headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    html_body = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="margin: 0; padding: 0; background-color: #0F172A; font-family: 'Malgun Gothic', '맑은 고딕', sans-serif;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 40px auto; background-color: #1E293B; border-radius: 20px; border: 1px solid #334155; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            <!-- Header -->
            <tr>
                <td style="padding: 36px 40px 20px 40px; text-align: center;">
                    <h1 style="color: #10B981; font-size: 26px; font-weight: 800; margin: 0;">
                        Blog<span style="color: #ffffff;">Automata</span>
                    </h1>
                    <p style="color: #94A3B8; font-size: 14px; margin-top: 8px; font-weight: 500;">
                        [{plan_name}] 라이선스 발급 안내
                    </p>
                </td>
            </tr>

            <!-- Content Body -->
            <tr>
                <td style="padding: 20px 40px 30px 40px;">
                    <p style="color: #F8FAFC; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
                        안녕하세요! <strong style="color: #10B981;">BlogAutomata</strong>를 이용해 주셔서 감사합니다.<br>
                        아래 발급된 라이선스 키를 프로그램 실행 후 입력하여 사용해 주세요.<br>
                        꼭 메일의 스팸함도 확인해 주세요!
                    </p>

                    <!-- License Box -->
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #0F172A; border: 1px solid #10B981; border-radius: 14px; margin-bottom: 24px;">
                        <tr>
                            <td style="padding: 24px; text-align: center;">
                                <span style="color: #94A3B8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 8px;">
                                    {plan_name} 라이선스 키
                                </span>
                                <span style="color: #10B981; font-size: 24px; font-weight: 800; letter-spacing: 2px; font-family: 'Courier New', monospace;">
                                    {license_key}
                                </span>
                            </td>
                        </tr>
                    </table>

                    <!-- Details -->
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #0F172A; border-radius: 10px; padding: 16px; color: #94A3B8; font-size: 13px; line-height: 1.8;">
                        <tr>
                            <td style="padding: 12px;">
                                • <strong>플랜 종류:</strong> <span style="color: #F8FAFC;">{plan_name}</span><br>
                                • <strong>만료 일시:</strong> <span style="color: #F8FAFC;">{expire_date_str}</span><br>
                                • 본 키는 최초 1회 프로그램 실행 시 등록된 PC(HWID)에 귀속됩니다.
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>

            <!-- Footer -->
            <tr>
                <td style="padding: 24px 40px; background-color: #0F172A; text-align: center; border-top: 1px solid #334155;">
                    <p style="color: #64748B; font-size: 12px; margin: 0; line-height: 1.5;">
                        본 메일은 발신 전용 메일입니다.<br>
                        © 2026 BlogAutomata. All rights reserved.
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    payload = {
        "from": "BlogAutomata <onboarding@resend.dev>",
        "to": [to_email],
        "subject": f"[BlogAutomata] {plan_name} 라이선스 키가 발급되었습니다.",
        "html": html_body
    }

    try:
        res = requests.post(resend_url, headers=email_headers, json=payload, timeout=10)
        if res.status_code in [200, 201]:
            print(f"✅ [{to_email}] Resend 메일 전송 성공!")
            return True
        else:
            print(f"❌ Resend 에러: {res.text}")
            return False
    except Exception as e:
        print(f"❌ 이메일 발송 중 예외 발생: {e}")
        return False


# --- 1. 3일 무료 체험 발급 API ---
@app.post("/api/issue-trial")
@app.post("/webhook/trial")
async def issue_trial_license(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 JSON 요청입니다.")
    
    user_email = data.get("email", "").strip()
    hwid = data.get("hwid", None)  # 클라이언트 프로그램에서 전달된 HWID (있을 경우)

    if not user_email or "@" not in user_email:
        raise HTTPException(status_code=400, detail="올바른 이메일 주소를 입력해주세요.")

    # 1-1) HWID 중복 체킹 (동일 HWID로 이미 무료 체험을 이용했는지 확인)
    if hwid:
        hwid_check_url = f"{SUPABASE_URL}/rest/v1/licenses?hwid=eq.{hwid}&plan_type=eq.trial"
        hwid_res = requests.get(hwid_check_url, headers=headers)
        if hwid_res.status_code == 200 and len(hwid_res.json()) > 0:
            raise HTTPException(status_code=400, detail="해당 PC(기기)는 이미 3일 무료 체험판을 사용하셨습니다.")

    # 1-2) 이메일 중복 체킹 (동일 이메일 존재 여부 DB 조회)
    check_url = f"{SUPABASE_URL}/rest/v1/licenses?user_email=eq.{user_email}"
    check_res = requests.get(check_url, headers=headers)
    
    if check_res.status_code == 200 and len(check_res.json()) > 0:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다. 유료 플랜 결제를 이용해 주세요.")

    # 2) 만료일(3일 뒤) 및 TRIAL 라이선스 키 생성
    expire_at = datetime.utcnow() + timedelta(days=3)
    expire_str = expire_at.strftime("%Y-%m-%d %H:%M:%S (UTC)")

    raw_key = str(uuid.uuid4()).upper().replace("-", "")
    trial_license_key = f"TRIAL-{raw_key[:4]}-{raw_key[4:8]}"

    # 3) Supabase DB 저장
    payload = {
        "license_key": trial_license_key,
        "user_email": user_email,
        "hwid": hwid,
        "plan_type": "trial",
        "is_active": True,
        "expire_date": expire_at.isoformat()
    }

    db_res = requests.post(f"{SUPABASE_URL}/rest/v1/licenses", headers=headers, json=payload)
    
    if db_res.status_code in [200, 201]:
        send_email_resend(user_email, trial_license_key, expire_str, "3일 무료 체험")
        return {
            "status": "success",
            "license_key": trial_license_key,
            "message": "체험판 라이선스가 이메일로 발송되었습니다."
        }
    else:
        raise HTTPException(status_code=500, detail="DB 등록 중 오류가 발생했습니다.")


# --- 2. 유료 결제 완료 및 플랜 업그레이드 API ---
@app.post("/api/payment/complete")
async def complete_payment(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 JSON 요청입니다.")

    payment_id = data.get("paymentId")
    user_email = data.get("userEmail", "").strip()
    plan_type = data.get("planType")  # 'monthly', 'yearly', 'lifetime'

    if not user_email or not plan_type:
        raise HTTPException(status_code=400, detail="필수 정보(이메일, 플랜)가 누락되었습니다.")

    # 만료일 계산 및 플랜명 세팅
    now = datetime.utcnow()
    if plan_type == "monthly":
        expire_at = now + timedelta(days=30)
        plan_name = "월간 플랜 (30일)"
        expire_str = expire_at.strftime("%Y-%m-%d %H:%M:%S (UTC)")
    elif plan_type == "yearly":
        expire_at = now + timedelta(days=365)
        plan_name = "연간 플랜 (1년)"
        expire_str = expire_at.strftime("%Y-%m-%d %H:%M:%S (UTC)")
    elif plan_type == "lifetime":
        expire_at = None
        plan_name = "영구 라이선스"
        expire_str = "무제한 (영구 사용)"
    else:
        raise HTTPException(status_code=400, detail="유효하지 않은 플랜 타입입니다.")

    # 기존 유저(체험판 사용 유저 포함) 여부 조회
    check_url = f"{SUPABASE_URL}/rest/v1/licenses?user_email=eq.{user_email}"
    check_res = requests.get(check_url, headers=headers)
    
    if check_res.status_code == 200 and len(check_res.json()) > 0:
        # 1) 기존 유저: 플랜 업그레이드 및 기간 연장
        existing_user = check_res.json()[0]
        license_key = existing_user["license_key"]
        
        update_payload = {
            "plan_type": plan_type,
            "is_active": True,
            "expire_date": expire_at.isoformat() if expire_at else None
        }
        
        update_url = f"{SUPABASE_URL}/rest/v1/licenses?user_email=eq.{user_email}"
        db_res = requests.patch(update_url, headers=headers, json=update_payload)
    else:
        # 2) 신규 유저: 새로 발급
        raw_key = str(uuid.uuid4()).upper().replace("-", "")
        license_key = f"{plan_type.upper()}-{raw_key[:4]}-{raw_key[4:8]}"
        
        insert_payload = {
            "license_key": license_key,
            "user_email": user_email,
            "hwid": None,
            "plan_type": plan_type,
            "is_active": True,
            "expire_date": expire_at.isoformat() if expire_at else None
        }
        db_res = requests.post(f"{SUPABASE_URL}/rest/v1/licenses", headers=headers, json=insert_payload)

    if db_res.status_code in [200, 201, 204]:
        send_email_resend(user_email, license_key, expire_str, plan_name)
        return {
            "status": "success",
            "message": "결제 및 라이선스 발급이 완료되었습니다.",
            "license_key": license_key
        }
    else:
        raise HTTPException(status_code=500, detail="DB 업데이트 및 결제 처리 중 오류가 발생했습니다.")


# --- 3. 오토 프로그램 라이선스 검증 API ---
@app.get("/api/verify-license")
def verify_license(license_key: str, hwid: str):
    if not license_key or not hwid:
        return {"valid": False, "reason": "라이선스 키와 HWID 값이 필요합니다."}

    url = f"{SUPABASE_URL}/rest/v1/licenses?license_key=eq.{license_key}"
    res = requests.get(url, headers=headers)

    if res.status_code != 200 or len(res.json()) == 0:
        return {"valid": False, "reason": "존재하지 않는 라이선스 키입니다."}

    license_info = res.json()[0]

    if not license_info.get("is_active"):
        return {"valid": False, "reason": "비활성화된 라이선스입니다."}

    # HWID 귀속 및 검증
    db_hwid = license_info.get("hwid")
    if not db_hwid:
        # 최초 실행 시 현재 PC의 HWID 등록
        update_url = f"{SUPABASE_URL}/rest/v1/licenses?license_key=eq.{license_key}"
        requests.patch(update_url, headers=headers, json={"hwid": hwid})
    elif db_hwid != hwid:
        return {"valid": False, "reason": "다른 PC에서 이미 등록되어 사용 중인 라이선스입니다."}

    # 만료일 검증 (영구 플랜인 경우 expire_date가 None)
    expire_date_str = license_info.get("expire_date")
    if expire_date_str:
        # ISO 포맷 파싱
        expire_date = datetime.fromisoformat(expire_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        if datetime.utcnow() > expire_date:
            return {"valid": False, "reason": "라이선스 유효기간이 만료되었습니다."}

    return {
        "valid": True,
        "plan_type": license_info.get("plan_type"),
        "user_email": license_info.get("user_email")
    }