import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { name, email, message } = body as {
      name?: string;
      email?: string;
      message?: string;
    };

    if (!name || !email || !message) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    const entry = { name, email, message, created_at: new Date().toISOString() };

    const dataDir = path.resolve(process.cwd(), 'data');
    await fs.mkdir(dataDir, { recursive: true });
    const filePath = path.join(dataDir, 'contacts.jsonl');
    await fs.appendFile(filePath, JSON.stringify(entry) + '\n', 'utf8');

    return NextResponse.json({ ok: true });
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('Contact API error', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

export async function GET() {
  try {
    const filePath = path.resolve(process.cwd(), 'data', 'contacts.jsonl');
    const content = await fs.readFile(filePath, 'utf8');
    const lines = content.trim().split('\n').filter(Boolean);
    const entries = lines.map((l) => JSON.parse(l));
    return NextResponse.json({ entries });
  } catch (err) {
    return NextResponse.json({ entries: [] });
  }
}
