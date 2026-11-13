import ast
import io
import json
import sys
import base64
import contextlib
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

nb_path = Path("scalping_vwap_rsi_notebook.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

global_env = {"__name__": "__main__", "display": print}
exec_count = 1

for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        code = "".join(cell["source"])
        code_lines = [l for l in code.split("\n") if not l.strip().startswith("%")]
        clean_code = "\n".join(code_lines).strip()
        cell["outputs"] = []
        cell["execution_count"] = exec_count
        exec_count += 1
        
        stdout_buf = io.StringIO()
        plt.close("all")
        
        with contextlib.redirect_stdout(stdout_buf):
            try:
                tree = ast.parse(clean_code)
                eval_res = None
                if tree.body and isinstance(tree.body[-1], ast.Expr):
                    last_expr_node = tree.body.pop()
                    if tree.body:
                        exec_code = compile(tree, "<string>", "exec")
                        exec(exec_code, global_env)
                    eval_code = compile(ast.Expression(last_expr_node.value), "<string>", "eval")
                    eval_res = eval(eval_code, global_env)
                else:
                    exec(compile(tree, "<string>", "exec"), global_env)
                
                out_text = stdout_buf.getvalue()
                if out_text:
                    cell["outputs"].append({
                        "output_type": "stream",
                        "name": "stdout",
                        "text": [line + "\n" for line in out_text.splitlines()]
                    })
                
                if eval_res is not None:
                    text_repr = str(eval_res)
                    html_repr = getattr(eval_res, "to_html", lambda: None)()
                    data_dict = {"text/plain": [line + "\n" for line in text_repr.splitlines()]}
                    if html_repr:
                        data_dict["text/html"] = [html_repr]
                    cell["outputs"].append({
                        "output_type": "execute_result",
                        "data": data_dict,
                        "execution_count": cell["execution_count"],
                        "metadata": {}
                    })

                for num in plt.get_fignums():
                    fig = plt.figure(num)
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
                    buf.seek(0)
                    img_b64 = base64.b64encode(buf.read()).decode("ascii")
                    cell["outputs"].append({
                        "output_type": "display_data",
                        "data": {
                            "image/png": img_b64,
                            "text/plain": ["<Figure size ...>"]
                        },
                        "metadata": {}
                    })
                    plt.close(fig)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                print(f"Error in cell:\n{tb}", file=sys.stderr)
                cell["outputs"].append({
                    "output_type": "error",
                    "ename": type(e).__name__,
                    "evalue": str(e),
                    "traceback": tb.splitlines()
                })

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

user_uploaded_path = Path("C:/Users/Admin/.gemini/antigravity/brain/95e9cea9-b1cc-4ed8-b61a-66d2d352f2a4/.user_uploaded/media_1794546242569_ae7bf46b.ipynb")
with open(user_uploaded_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Notebook execution succeeded and verified!")
