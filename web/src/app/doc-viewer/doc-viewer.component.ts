import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MarkdownModule } from 'ngx-markdown';
import { Document } from '../sentinel.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-doc-viewer',
  imports: [CommonModule, MatDialogModule, MatButtonModule, MarkdownModule],
  templateUrl: './doc-viewer.component.html',
  styleUrl: './doc-viewer.component.css',
})
export class DocViewerComponent {
  data = inject(MAT_DIALOG_DATA);
  document: Document = this.data.document;

  constructor() {}
}
